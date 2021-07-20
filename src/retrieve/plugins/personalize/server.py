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

from google.protobuf import descriptor
from google.protobuf import any_pb2
import grpc
from grpc_reflection.v1alpha import reflection
from google.protobuf.any_pb2 import Any
from concurrent import futures

import service_pb2
import service_pb2_grpc

app = FastAPI()


# Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'PERSONALIZE_PORT': 6500,
    'AWS_REGION': 'ap-northeast-1',
    'PERSONALIZE_DATASET_GROUP': 'GCR-RS-News-Dataset-Group',
    'PERSONALIZE_SOLUTION': 'userPersonalizeSolution',
    'PERSONALIZE_CAMPAIGN': 'gcr-rs-dev-workshop-news-userPersonalize-campaign',
    'EVENT_TRACKER': 'NewsEventTracker'
}


class Retrieve(service_pb2_grpc.RankServicer):

    def __init__(self):
        logging.info('__init__(self)...')
        # 建立连接
        self.personalize = boto3.client('personalize', MANDATORY_ENV_VARS['AWS_REGION'])
        self.personalize_runtime = boto3.client('personalize-runtime', MANDATORY_ENV_VARS['AWS_REGION'])
        self.personalize_events = boto3.client(service_name='personalize-events',
                                               region_name=MANDATORY_ENV_VARS['AWS_REGION'])

        self.dataset_group_arn = self.get_dataset_group_arn()
        self.solution_arn = self.get_solution_arn()
        self.campaign_arn = self.get_campaign_arn()
        self.event_tracker_arn = self.get_event_tracker_arn()
        self.event_tracker_id = self.get_event_tracking_id()

    def get_dataset_group_arn(self):
        datasetGroups = self.personalize.list_dataset_groups()
        for dataset_group in datasetGroups["datasetGroups"]:
            if dataset_group["name"] == MANDATORY_ENV_VARS['PERSONALIZE_DATASET_GROUP']:
                logging.info("Dataset Group Arn:{}".format(dataset_group["datasetGroupArn"]))
                return dataset_group["datasetGroupArn"]

    def get_solution_arn(self):
        solutions = self.personalize.list_solutions(
            datasetGroupArn=self.dataset_group_arn
        )
        for solution in solutions["solutions"]:
            if solution['name'] == MANDATORY_ENV_VARS['PERSONALIZE_SOLUTION']:
                logging.info("Solution Arn:{}".format(solution["solutionArn"]))
                return solution["solutionArn"]

    def get_campaign_arn(self):
        campaigns = self.personalize.list_campaigns(
            solutionArn=self.solution_arn
        )
        for campaign in campaigns["campaigns"]:
            if campaign["name"] == MANDATORY_ENV_VARS['PERSONALIZE_CAMPAIGN']:
                logging.info("Campaign Arn:{}".format(campaign["campaignArn"]))
                return campaign["campaignArn"]

    def get_event_tracker_arn(self):
        eventTrackers = self.personalize.list_event_trackers(
            datasetGroupArn=self.dataset_group_arn
        )
        for event_tracker in eventTrackers["eventTrackers"]:
            if event_tracker['name'] == MANDATORY_ENV_VARS['EVENT_TRACKER']:
                logging.info("Event Tracker Arn:{}".format(event_tracker["eventTrackerArn"]))
                return event_tracker["eventTrackerArn"]

    def get_event_tracking_id(self):
        eventTracker = self.personalize.describe_event_tracker(
            eventTrackerArn=self.event_tracker_arn
        )
        logging.info("Event Tracker ID:{}".format(eventTracker["eventTracker"]["trackingId"]))
        return eventTracker["eventTracker"]["trackingId"]

    def GetRecommendData(self, request, context):
        logging.info("personalize plugin GetRecommendData start...")
        # Retrieve request data
        request_body = Any()
        request.requestBody.Unpack(request_body)
        reqData = json.loads(request_body.value, encoding='utf-8')
        user_id = reqData['user_id']
        logging.info('user_id -> {}'.format(user_id))

        item_list = self.get_recommend_data(user_id)

        logging.info("-----------recommend list:{}".format(item_list))
        logging.info('GetFilterData start')

        getRecommendDataResponseValue = {
            'data': item_list
        }

        getRecommendDataResponseAny = Any()
        getRecommendDataResponseAny.value = json.dumps(getRecommendDataResponseValue).encode('utf-8')
        getRecommendDataResponse = service_pb2.GetRecommendDataResponse(code=0, description='personalize plugin process with success')
        getRecommendDataResponse.results.Pack(getRecommendDataResponseAny)

        logging.info("get recommend data complete")

        return getRecommendDataResponse

    def get_recommend_data(self, user_id):
        # trigger personalize api
        get_recommendations_response = self.personalize_runtime.get_recommendations(
            campaignArn=self.campaign_arn,
            userId=str(user_id),
        )
        # 为推荐列表构建新的 Dataframe
        result_list = get_recommendations_response['itemList']
        item_list = []
        for item in result_list:
            item_list.append({
                "id": item['itemId'],
                "description": 'personalize|{}'.format(str(item['score'])),
                "tag": 'recommend'
            })
        return item_list



def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)

    # # Initial redis connection
    # global rCache
    # rCache = cache.RedisCache(host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])


def serve(plugin_name):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    service_pb2_grpc.add_RetrieveServicer_to_server(Retrieve(), server)
    SERVICE_NAMES = (
        service_pb2.DESCRIPTOR.services_by_name['Retrieve'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logging.info('Plugin - %s is listening at 50051...', plugin_name)
    server.add_insecure_port('[::]:50051')
    logging.info('Plugin - %s is ready to serve...', plugin_name)
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    print('Retrieve plugin start')
    init()
    serve(os.environ.get("PLUGIN_NAME", "default"))