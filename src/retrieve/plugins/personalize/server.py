import json
import logging
import os
import pickle
import random
import sys
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
    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',
    'NEWS_ID_PROPERTY': 'news_id_news_property_dict.pickle',
    'NEWS_TYPE_NEWS_IDS': 'news_type_news_ids_dict.pickle',
    'RECOMMEND_ITEM_COUNT': 20,

    'AWS_REGION': 'ap-northeast-1',
    'PERSONALIZE_DATASET_GROUP': 'GCR-RS-News-Dataset-Group',
    'PERSONALIZE_SOLUTION': 'userPersonalizeSolution',
    'PERSONALIZE_CAMPAIGN': 'gcr-rs-dev-workshop-news-userPersonalize-campaign',
}

lCfgCompleteType = ['news_story', 'news_culture', 'news_entertainment', 'news_sports', 'news_finance', 'news_house', 'news_car', 'news_edu', 'news_tech', 'news_military', 'news_travel', 'news_world', 'stock', 'news_agriculture', 'news_game']

class Retrieve(service_pb2_grpc.RetrieveServicer):

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

        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        file_list = [MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS']]
        file_list.append(MANDATORY_ENV_VARS['NEWS_ID_PROPERTY'])
        self.reload_pickle_type(local_data_folder, file_list, False)

    def reload_pickle_type(self, file_path, file_list, reloadFlag):
        logging.info('reload_pickle_type strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['NEWS_ID_PROPERTY'] in pickle_path:
                logging.info('reload news_id_news_property_dict file {}'.format(pickle_path))
                self.news_id_news_property_dict = self.load_pickle(pickle_path)
            elif MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'] in pickle_path:
                logging.info('reload news_type_news_ids_dict file {}'.format(pickle_path))
                self.news_type_news_ids_dict = self.load_pickle(pickle_path)
                self.lCfgCompleteType = list(self.news_type_news_ids_dict.keys())

    def load_pickle(self, file):
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = pickle.load(infile)
            infile.close()
            return dict
        else:
            return {}

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

    def GetRecommendData(self, request, context):
        logging.info("personalize plugin GetRecommendData start...")
        # Retrieve request data
        request_body = Any()
        request.requestBody.Unpack(request_body)
        reqData = json.loads(request_body.value, encoding='utf-8')
        user_id = reqData['user_id']
        recommend_type = reqData['recommend_type']
        logging.info('user_id -> {}'.format(user_id))
        logging.info('recommend_type -> {}'.format(recommend_type))

        item_list = self.get_recommend_data(user_id, recommend_type)

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

    def get_recommend_data(self, user_id, recommend_type):
        logging.info('get_personalize_recommend_result start!!')
        item_list = []
        if recommend_type == 'recommend':
            # trigger personalize api
            get_recommendations_response = self.personalize_runtime.get_recommendations(
                campaignArn=self.campaign_arn,
                userId=str(user_id),
            )
            # 为推荐列表构建新的 Dataframe
            result_list = get_recommendations_response['itemList']
            for item in result_list:
                item_list.append({
                    "id": item['itemId'],
                    "description": 'personalize|{}'.format(str(item['score'])),
                    "tag": 'recommend'
                })
        else:
            logging.info('get news list by news type {}'.format(recommend_type))
            if recommend_type not in self.lCfgCompleteType:
                return item_list
            logging.info('Get news_type_news_ids_dict completed')
            if not bool(self.news_type_news_ids_dict):
                return item_list
            news_id_list = self.news_type_news_ids_dict[recommend_type]
            item_list = self.generate_news_list_by_type(news_id_list)

        return item_list

    def generate_news_list_by_type(self, news_id_list):
        news_recommend_list = []
        count = 0
        present_recommend_news_id_list = []
        try_count = 0
        need_count = int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT'])
        while count < need_count:
            news, news_id = self.get_random_news(news_id_list)
            try_count = try_count + 1
            if news_id not in present_recommend_news_id_list:
                news_recommend_list.append(news)
                present_recommend_news_id_list.append(news_id)
                count = count + 1
            if try_count > need_count * 3:
                logging.error(
                    "fail to find enough candidate in generate_news_list_by_type, need to find {} but only find {}".format(need_count,
                                                                                                    count))
                break

        return news_recommend_list

    def get_random_news(self, news_id_list):
        logging.info('get_random_news_id start')
        index = random.randint(0,len(news_id_list) -1)
        return {
            'id': news_id_list[index],
            'tag': 'type',
            'description': 'get the list of type'
        }, news_id_list[index]


def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)

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