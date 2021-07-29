import math
from typing import List
import uvicorn
from fastapi import FastAPI
import sys
import boto3
import json
import logging
import os
import time
from pydantic import BaseModel
from botocore import config

app = FastAPI()


#Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'PERSONALIZE_PORT': 6500,
    'AWS_REGION': 'ap-northeast-1',
    'PERSONALIZE_DATASET_GROUP': 'GCR-RS-News-Ranking-Dataset-Group',
    'PERSONALIZE_SOLUTION': 'rankingSolution',
    'PERSONALIZE_CAMPAIGN': 'gcr-rs-dev-workshop-news-ranking-campaign',
    'EVENT_TRACKER': 'NewsRankingEventTracker'
}

class Metadata(BaseModel):
    type: str

class ClickPersonalizeRequest(BaseModel):
    user_id: str
    item_id: str

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

@app.get('/personalize/status', tags=["monitoring"])
def status():
    logging.info('Collecting status information from server...')
    return {
        'env': MANDATORY_ENV_VARS,
    }

@app.get('/ping', tags=["monitoring"])
def ping():
    logging.info('Processing default request...')
    return { 'result': 'ping' }

@app.post("/personalize/click", tags=["personalize_click"])
def personalize_click(clickPersonalizeRequest: ClickPersonalizeRequest):
    #     try:
    #         session_ID = session_dict[str(user_id)]
    #     except:
    #         session_dict[str(user_id)] = str(uuid.uuid1())
    #         session_ID = session_dict[str(user_id)]

    user_id = clickPersonalizeRequest.user_id
    item_id = clickPersonalizeRequest.item_id

    #   暂时用 userID 替代为 sessionID
    session_ID = user_id
    logging.info("userId: {}".format(user_id))
    logging.info("itemId: {}".format(item_id))

    response = personalize_events.put_events(
        trackingId=tracking_id,
        userId=user_id,
        sessionId=session_ID,
        eventList=[{
            'sentAt': int(time.time()),
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
        campaignArn=campaign_arn,
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
        campaignArn=campaign_arn,
        userId=str(user_id),
    )

    # 为推荐列表构建新的 Dataframe
    item_list = get_recommendations_response['itemList']
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
    for dataset_group in response["datasetGroups"]:
        if dataset_group["name"] == MANDATORY_ENV_VARS['PERSONALIZE_DATASET_GROUP']:
            logging.info("Dataset Group Arn:{}".format(dataset_group["datasetGroupArn"]))
            return dataset_group["datasetGroupArn"]

def get_campaign_arn():
    solutions = personalize.list_solutions(
        datasetGroupArn=dataset_group_arn
    )
    solution_arn = ''
    for solution in solutions["solutions"]:
        if solution['name'] == MANDATORY_ENV_VARS['PERSONALIZE_SOLUTION']:
            solution_arn = solution["solutionArn"]
    campaigns = personalize.list_campaigns(
        solutionArn=solution_arn
    )
    for campaign in campaigns["campaigns"]:
        if campaign["name"] == MANDATORY_ENV_VARS['PERSONALIZE_CAMPAIGN']:
            logging.info("Campaign Arn:{}".format(campaign["campaignArn"]))
            return campaign["campaignArn"]

def get_event_tracker_arn():
    eventTrackers = personalize.list_event_trackers(
        datasetGroupArn=dataset_group_arn
    )
    for event_tracker in eventTrackers["eventTrackers"]:
        if event_tracker['name'] == MANDATORY_ENV_VARS['EVENT_TRACKER']:
            logging.info("Event Tracker Arn:{}".format(event_tracker["eventTrackerArn"]))
            return event_tracker["eventTrackerArn"]


def get_tracking_id():
    response_event_tracker = personalize.describe_event_tracker(
        eventTrackerArn=event_tracker_arn
    )
    logging.info("Event Tracker ID:{}".format(response_event_tracker["eventTracker"]["trackingId"]))   
    return response_event_tracker["eventTracker"]["trackingId"]


def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)

    # 建立连接
    global personalize
    global personalize_runtime
    global personalize_events
    personalize = boto3.client('personalize', MANDATORY_ENV_VARS['AWS_REGION'])
    personalize_runtime = boto3.client('personalize-runtime', MANDATORY_ENV_VARS['AWS_REGION'])
    personalize_events = boto3.client(service_name='personalize-events', region_name=MANDATORY_ENV_VARS['AWS_REGION'])

    global dataset_group_arn
    dataset_group_arn = get_dataset_group_arn()

    global campaign_arn
    campaign_arn = get_campaign_arn()

    global event_tracker_arn
    event_tracker_arn = get_event_tracker_arn()

    global tracking_id
    tracking_id = get_tracking_id()


if __name__ == '__main__':
    print('server start')
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    init()
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['PERSONALIZE_PORT'])













