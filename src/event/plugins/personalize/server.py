import json
import logging
import os
import sys
import time
from concurrent import futures

import boto3
import grpc
import service_pb2
import service_pb2_grpc
from fastapi import FastAPI
from google.protobuf.any_pb2 import Any
from grpc_reflection.v1alpha import reflection

app = FastAPI()

# Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'AWS_REGION': 'ap-northeast-1',
    'PERSONALIZE_DATASET_GROUP': 'GCR-RS-News-Dataset-Group',
    'EVENT_TRACKER': 'NewsEventTracker'
}


class Event(service_pb2_grpc.EventServicer):

    def __init__(self):
        logging.info('__init__(self)...')
        # 建立连接
        self.personalize = boto3.client('personalize', MANDATORY_ENV_VARS['AWS_REGION'])
        self.personalize_runtime = boto3.client('personalize-runtime', MANDATORY_ENV_VARS['AWS_REGION'])
        self.personalize_events = boto3.client(service_name='personalize-events',
                                               region_name=MANDATORY_ENV_VARS['AWS_REGION'])
        self.dataset_group_arn = self.get_dataset_group_arn()
        self.event_tracker_arn = self.get_event_tracker_arn()
        self.event_tracker_id = self.get_event_tracking_id()
        self.user_dataset_arn = self.get_user_dataset_arn()

    def get_dataset_group_arn(self):
        datasetGroups = self.personalize.list_dataset_groups()
        for dataset_group in datasetGroups["datasetGroups"]:
            if dataset_group["name"] == MANDATORY_ENV_VARS['PERSONALIZE_DATASET_GROUP']:
                logging.info("Dataset Group Arn:{}".format(dataset_group["datasetGroupArn"]))
                return dataset_group["datasetGroupArn"]

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

    def get_user_dataset_arn(self):
        datasets = self.personalize.list_datasets(
            datasetGroupArn=self.dataset_group_arn
        )
        for dataset in datasets['datasets']:
            if dataset['datasetType'] == 'USERS':
                logging.info('User Dataset Arn:{}'.format(dataset['datasetArn']))
                return dataset['datasetArn']

    def get_solution_arn(self, solutionName):
        solutions = self.personalize.list_solutions(
            datasetGroupArn=self.dataset_group_arn
        )
        for solution in solutions["solutions"]:
            if solution['name'] == solutionName:
                logging.info("Solution Arn:{}".format(solution["solutionArn"]))
                return solution["solutionArn"]


    def EventTracker(self, request, context):
        logging.info("personalize plugin EventTracker start...")
        # Event Tracker
        request_body = Any()
        request.requestBody.Unpack(request_body)
        reqData = json.loads(request_body.value, encoding='utf-8')
        user_id = reqData['user_id']
        items_id = reqData['clicked_item_ids']
        #   暂时用 userID 替代为 sessionID
        session_ID = user_id
        logging.info('user_id -> {}'.format(user_id))
        logging.info('items_id -> {}'.format(items_id))

        for item_id in items_id:
            curTime = int(time.time())
            self.personalize_events.put_events(
                trackingId=self.event_tracker_id,
                userId=user_id,
                sessionId=session_ID,
                eventList=[{
                    'sentAt': curTime,
                    'itemId': item_id,
                    'eventType': 'CLICK'
                }]
            )

        eventTrackerResponse = service_pb2.EventTrackerResponse(code=0,
                                                                description='personalize plugin process with success')
        logging.info("event track complete")
        return eventTrackerResponse

    def AddNewUser(self, request, context):
        logging.info("personalize plugin AddNewUser start ...")
        request_body = Any()
        request.requestBody.Unpack(request_body)
        reqData = json.loads(request_body.value, encoding='utf-8')
        user_id = reqData['userId']
        user_sex = reqData['gender']
        logging.info("user_id:{}, user_gender:{}".format(user_id, user_sex))

        self.personalize_events.put_users(
            datasetArn=self.user_dataset_arn,
            users=[
                {
                    'userId': user_id,
                    'properties': str({
                        'gender': user_sex
                    })
                },
            ]
        )

        addNewUserResponse = service_pb2.AddNewUserResponse(code=0,
                                                            description='personalize plugin add new user process with success')
        logging.info("add new user complete")
        return addNewUserResponse


def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)


def serve(plugin_name):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    service_pb2_grpc.add_EventServicer_to_server(Event(), server)
    SERVICE_NAMES = (
        service_pb2.DESCRIPTOR.services_by_name['Event'].full_name,
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
    print('Event plugin start')
    init()
    serve(os.environ.get("PLUGIN_NAME", "default"))
