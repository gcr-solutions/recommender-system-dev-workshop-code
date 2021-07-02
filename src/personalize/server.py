import uvicorn
from fastapi import FastAPI
import grpc
import sys
import service_pb2
import service_pb2_grpc
import boto3
import json
import logging
import os
import time
from threading import Thread
from google.protobuf import any_pb2

app = FastAPI()

#Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'PERSONALIZE_PORT': 6500
}

#Notice channel
sleep_interval = 10 #second


def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target = f, args = args, kwargs = kwargs)
        thr.start()
    return wrapper

# @app.get('/personalize/status', tags=["monitoring"])
# def status():
#     logging.info('Collecting status information from server & plugin...')
#     channel = grpc.insecure_channel('localhost:50051')
#     stub = service_pb2_grpc.PersonalizeStub(channel)
#     response = stub.Status(service_pb2.google_dot_protobuf_dot_empty__pb2.Empty())
#     statusAny = any_pb2.Any()
#     response.status.Unpack(statusAny)
#
#     pStatus = json.loads(statusAny.value.decode('utf-8'))
#     return {
#         'env': MANDATORY_ENV_VARS,
#         'redis': rCache.connection_status(),
#         'plugin_status': pStatus
#     }

@app.get('/ping', tags=["monitoring"])
def ping():
    logging.info('Processing default request...')
    return { 'result': 'ping' }


session_dict = {}
@app.post("/personalize/click", tags=["personalize_click"])
def personalize_click(user_id: str, item_id: int, event_type: str):
    #     try:
    #         session_ID = session_dict[str(user_id)]
    #     except:
    #         session_dict[str(user_id)] = str(uuid.uuid1())
    #         session_ID = session_dict[str(user_id)]

    #   暂时用 userID 替代为 sessionID
    session_ID = user_id

    event = str(item_id)
    event_json = json.dumps(event)

    personalize_events.put_events(
        trackingId=tracking_id,
        userId=str(user_id),
        sessionId=session_ID,
        eventList=[{
            'sentAt': int(time.time()),
            'eventType': str(event_type),
            'itemId': item_id
        }]
    )


@app.get("/personalize/retrieve", tags=["personalize_retrieve"])
def personalize_get_recommendations(user_id: str):

    # 为该用户获得推荐
    get_recommendations_response = personalize_runtime.get_recommendations(
        campaignArn=userpersonalization_campaign_arn,
        userId=str(user_id),
    )

    # 为推荐列表构建新的 Dataframe
    item_list = get_recommendations_response['itemList']
    recommendation_list = []
    for item in item_list:
        recommendation_list.append(item)
    return recommendation_list


def get_dataset_group_arn():
    response = personalize.list_dataset_groups()
    return response["datasetGroups"][0]["datasetGroupArn"]


def get_userpersonalization_campaign_arn():
    solution_Arn = ''
    response = personalize.list_solutions(
        datasetGroupArn=dataset_group_arn
    )
    for solution in response["solutions"]:
        if solution['name'] == 'personalize-poc-userpersonalization':
            solution_Arn = solution["solutionArn"]

    response = personalize.list_campaigns(
        solutionArn=solution_Arn
    )
    return response["campaigns"][0]["campaignArn"]


def get_event_tracker_arn():
    response_dataset_group = personalize.list_event_trackers(
        datasetGroupArn=dataset_group_arn
    )
    eventTracker = response_dataset_group["eventTrackers"][0]
    return eventTracker["eventTrackerArn"]


def get_tracking_id():
    response_event_tracker = personalize.describe_event_tracker(
        eventTrackerArn=event_tracker_arn
    )
    return response_event_tracker["eventTracker"]["trackingId"]



def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)

    ## 建立与 Personalize 的连接
    global personalize
    global personalize_runtime
    global personalize_events
    personalize = boto3.client('personalize')
    personalize_runtime = boto3.client('personalize-runtime')
    personalize_events = boto3.client(service_name='personalize-events')

    global dataset_group_arn
    dataset_group_arn = get_dataset_group_arn()

    global userpersonalization_campaign_arn
    userpersonalization_campaign_arn = get_userpersonalization_campaign_arn()

    global event_tracker_arn
    event_tracker_arn = get_event_tracker_arn()

    global tracking_id
    tracking_id = get_tracking_id()

    print(dataset_group_arn)
    print()
    print(tracking_id)
    print(event_tracker_arn)


if __name__ == '__main__':
    print('server start')
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    init()
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['PERSONALIZE_PORT'])













