import json
import logging
import os
import time
import uuid
from threading import Thread

import boto3
import grpc
import pandas as pd
from fastapi import FastAPI
from google.protobuf import any_pb2
from pydantic import BaseModel

from src.portrait.plugins.default.test_cache import rCache


class ProcessItem(BaseModel):
    user_id: str
    clicked_item_ids: list = []

app = FastAPI()

#Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'PERSONALIZE_PORT': 6500
}

#Notice channel
sleep_interval = 10 #second


## TODO
# dataset_group_arn = ''
# userpersonalization_campaign_arn = ''

def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target = f, args = args, kwargs = kwargs)
        thr.start()
    return wrapper

@app.get('/personalize/status', tags=["monitoring"])
def status():
    logging.info('Collecting status information from server & plugin...')
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.PersonalizeStub(channel)
    response = stub.Status(service_pb2.google_dot_protobuf_dot_empty__pb2.Empty())
    statusAny = any_pb2.Any()
    response.status.Unpack(statusAny)

    pStatus = json.loads(statusAny.value.decode('utf-8'))
    return {
        'env': MANDATORY_ENV_VARS,
        'redis': rCache.connection_status(),
        'plugin_status': pStatus
    }

@app.get('/ping', tags=["monitoring"])
def ping():
    logging.info('Processing default request...')
    return { 'result': 'ping' }


session_dict = {}
@app.post("/personalize/click", tags=["personalize_click"])
def personalize_click(user_id: str, item_id: int, event_type: str):
    try:
        session_ID = session_dict[str(user_id)]
    except:
        session_dict[str(user_id)] = str(uuid.uuid1())
        session_ID = session_dict[str(user_id)]

    event = str(item_id)
    event_json = json.dumps(event)

    personalize_events.put_events(
        trackingId = TRACKING_ID,
        userId = str(user_id),
        sessionID = session_ID,
        eventList = [{
            'sentAt': int(time.time()),
            'eventType': str(event_type),
            'properties': event_json
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



def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)

    ## 建立与 Personalize 的连接
    personalize = boto3.client('personalize')
    personalize_runtime = boto3.client('personalize-runtime')
    personalize_events = boto3.client(service_name='personalize-events')

    global dataset_group_arn
    global userpersonalization_campaign_arn
    dataset_group_arn = personalize.list_dataset_groups()
    print(dataset_group_arn)

    # initial personalize connection
    response = personalize.create_event_tracker(
        name='tracker',
        datasetGroupArn=dataset_group_arn
    )

    global TRACKING_ID
    global event_tracker_arn
    TRACKING_ID = response['trackingId']
    event_tracker_arn = response['eventTrackerArn']



if __name__ == '__main__':
    init()












