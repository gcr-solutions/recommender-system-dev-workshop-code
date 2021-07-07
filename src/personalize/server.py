import math
from typing import List

import uvicorn
from fastapi import FastAPI
# import grpc
import sys
# import service_pb2
# import service_pb2_grpc
import boto3
import json
import logging
import os
import time
from threading import Thread
from pydantic import BaseModel
# from google.protobuf import any_pb2
# import redis
# import cache
from botocore import config

app = FastAPI()

#Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'PERSONALIZE_PORT': 6500,
    'AWS_REGION': 'ap-northeast-1'
}

class Metadata(BaseModel):
    type: str

class ClickPersonalizeRequest(BaseModel):
    user_id: str
    item_id: str
    event_type: str

class RerankRequest(BaseModel):
    user_id: str
    item_list: List[str]

class RSItem(BaseModel):
    id: str
    tags: List[str]
    description: str

class Pagination(BaseModel):
    curPage: int
    pageSize: int
    totalSize: int
    totalPage: int

class RecommendList(BaseModel):
    version: int = 1
    metadata: Metadata
    content: List[RSItem]
    pagination: Pagination

#Notice channel
sleep_interval = 10 #second

def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target = f, args = args, kwargs = kwargs)
        thr.start()
    return wrapper
#
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
def personalize_click(clickPersonalizeRequest: ClickPersonalizeRequest):
    #     try:
    #         session_ID = session_dict[str(user_id)]
    #     except:
    #         session_dict[str(user_id)] = str(uuid.uuid1())
    #         session_ID = session_dict[str(user_id)]

    user_id = clickPersonalizeRequest.user_id
    item_id = clickPersonalizeRequest.item_id
    event_type = clickPersonalizeRequest.event_type

    #   暂时用 userID 替代为 sessionID
    session_ID = user_id
    logging.info("userId: {}".format(user_id))
    logging.info("itemId: {}".format(item_id))
    logging.info("eventType: {}".format(event_type))


    response = personalize_events.put_events(
        trackingId=tracking_id,
        userId=user_id,
        sessionId=session_ID,
        eventList=[{
            'sentAt': int(time.time()),
            'eventType': event_type,
            'itemId': item_id
        }]
    )

    response_json = json.dumps(response)
    logging.info(response_json)



@app.post("/personalize/rerank", tags=["personalize_rerank"])
def personalize_rerank(rerankRequest: RerankRequest):
    user_id = rerankRequest.user_id
    item_list = rerankRequest.item_list

    logging.info("send get_personalized_ranking to aws personalize...")
    response = personalize_runtime.get_personalized_ranking(
        campaignArn=ranking_campaign_arn,
        inputList=item_list,
        userId=user_id
    )
    rank_list = response['personalizedRanking']
    presults = {}
    for rank_item in rank_list:
        presults[rank_item['itemId']] = rank_item['score']
    return presults


@app.get("/personalize/retrieve", tags=["personalize_retrieve"])
def personalize_get_recommendations(user_id: str,curPage: int = 0, pageSize: int = 10):

    # 为该用户获得推荐
    get_recommendations_response = personalize_runtime.get_recommendations(
        campaignArn=userpersonalization_campaign_arn,
        userId=str(user_id),
    )

    # 为推荐列表构建新的 Dataframe
    item_list = get_recommendations_response['itemList']
    # recommendation_list = []
    # for item in item_list:
    #     data = {
    #         'id': item['itemId'],
    #         'tags': ['recommend']
    #     }
    #     recommendation_list.append(data)

    it_list = [RSItem(id=str(it['itemId']), description='test description', tags=['recommend']) for it in item_list]
    it_list_paged = it_list[curPage * pageSize: (curPage + 1) * pageSize]
    total_page = math.ceil(len(it_list) / pageSize)

    content = it_list_paged
    pagination = Pagination(curPage=curPage, pageSize=pageSize,
                            totalSize=len(it_list),
                            totalPage=total_page)

    rs_list = RecommendList(
        metadata=Metadata(type="RecommendList"),
        content=content,
        pagination=pagination
    )

    return rs_list


def get_dataset_group_arn():
    response = personalize.list_dataset_groups()
    return response["datasetGroups"][0]["datasetGroupArn"]

def get_ranking_campaign_arn():
    solution_arn = ''
    response = personalize.list_solutions(
        datasetGroupArn=dataset_group_arn
    )
    for solution in response["solutions"]:
        if solution['name'] == 'rankingSolution':
            solution_arn = solution["solutionArn"]

    response = personalize.list_campaigns(
        solutionArn=solution_arn
    )
    return response["campaigns"][0]["campaignArn"]


def get_userpersonalization_campaign_arn():
    solution_Arn = ''
    response = personalize.list_solutions(
        datasetGroupArn=dataset_group_arn
    )
    for solution in response["solutions"]:
        if solution['name'] == 'userPersonalizeSolution':
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

    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    # 建立连接
    global personalize
    global personalize_runtime
    global personalize_events
    personalize = boto3.client('personalize', aws_region)
    personalize_runtime = boto3.client('personalize-runtime', aws_region)
    personalize_events = boto3.client(service_name='personalize-events', region_name=aws_region)



    global dataset_group_arn
    dataset_group_arn = get_dataset_group_arn()

    global userpersonalization_campaign_arn
    userpersonalization_campaign_arn = get_userpersonalization_campaign_arn()

    global ranking_campaign_arn
    ranking_campaign_arn = get_ranking_campaign_arn()

    global event_tracker_arn
    event_tracker_arn = get_event_tracker_arn()

    global tracking_id
    tracking_id = get_tracking_id()

    print(dataset_group_arn)
    print(userpersonalization_campaign_arn)
    print(tracking_id)
    print(event_tracker_arn)


if __name__ == '__main__':
    print('server start')
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    init()
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['PERSONALIZE_PORT'])













