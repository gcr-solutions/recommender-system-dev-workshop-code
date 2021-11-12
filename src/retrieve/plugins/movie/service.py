from concurrent import futures
import logging
import os
import json
from datetime import datetime
import pickle
import requests
import calendar
import time
import numpy as np
import random
from random import sample
import sys
import time
import boto3
import glob

from google.protobuf import descriptor
from google.protobuf import any_pb2
import grpc
from grpc_reflection.v1alpha import reflection
from google.protobuf.any_pb2 import Any

import cache

import service_pb2
import service_pb2_grpc

# Environments for service
MANDATORY_ENV_VARS = {

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,

    'MOVIE_CATEGORY_MOVIE_IDS': 'movie_category_movie_ids_dict.pickle',

    'RECOMMEND_ITEM_COUNT': 100,
    'COLDSTART_MOVIE_COUNT': 100,
    'PORTRAIT_SERVICE_ENDPOINT': 'http://portrait:5300',
    'PS_CONFIG': 'ps_config.json',
    'AWS_REGION': 'ap-northeast-1',
    'METHOD': 'ps-complete'
}

##
user_id_filter_dict='user_id_filter_dict' 
user_id_personalize_dict='user_id_personalize_dict'

tColdstart = 'coldstart'
hot_topic_count_array = [2,3]
pickle_type = 'inverted-list'
json_type = 'ps-result'
tRecommend = 'recommend'

# lastUpdate
localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

class Retrieve(service_pb2_grpc.RetrieveServicer):

    def __init__(self):
        logging.info('__init__(self)...')
        # TODO load data for filter, get parameters from stream
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        file_list = [MANDATORY_ENV_VARS['MOVIE_CATEGORY_MOVIE_IDS']]

        self.reload_pickle_type(local_data_folder, file_list, False)
        json_file_list = [MANDATORY_ENV_VARS['PS_CONFIG']]
        self.reload_json_type(local_data_folder, json_file_list)
        self.personalize_runtime = boto3.client('personalize-runtime', MANDATORY_ENV_VARS['AWS_REGION'])

    def Reload(self, request, context):
        logging.info('Restart(self, request, context)...')
        requestMessage = Any()
        request.dicts.Unpack(requestMessage)
        logging.info('Recieved notice requestMessage -> {}'.format(requestMessage))
        requestMessageJson = json.loads(requestMessage.value, encoding='utf-8')
        file_type = requestMessageJson['file_type']
        file_list = eval(requestMessageJson['file_list'])
        logging.info('file_type -> {}'.format(file_type))
        logging.info('file_list -> {}'.format(file_list)) 

        self.check_files_ready(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list, 0)
        if file_type == pickle_type:
            self.reload_pickle_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list, True)
        elif file_type == json_type:
            self.reload_json_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)

        logging.info('Re-initial filter service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse 

    def reload_pickle_type(self, file_path, file_list, reloadFlag):
        logging.info('reload_pickle_type strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))                 
            if MANDATORY_ENV_VARS['MOVIE_CATEGORY_MOVIE_IDS'] in pickle_path:
                logging.info('reload movie_category_movie_ids_dict file {}'.format(pickle_path))
                self.movie_category_movie_ids_dict = self.load_pickle(pickle_path) 
                self.lCfgCompleteType = list(self.movie_category_movie_ids_dict.keys())

    def reload_json_type(self, file_path, file_list):
        logging.info('reload_json_type start')
        for file_name in file_list:
            json_path = file_path + file_name
            logging.info('reload_json_type json_path {}'.format(json_path))
            if MANDATORY_ENV_VARS['PS_CONFIG'] in json_path:
                if os.path.isfile(json_path):
                    logging.info('reload ps_config file {}'.format(json_path))
                    self.ps_config = self.load_json(json_path)
                else:
                    logging.info('reload ps_config failed, file is empty')

    def check_files_ready(self, file_path, file_list, loop_count):
        logging.info('start check files are ready: path {}, file_list {}'.format(file_path, file_list))
        check_again_flag = False
        check_file_list = []
        for file_name in file_list:
            pickle_path = file_path + file_name 
            if not os.path.isfile(pickle_path):
                check_again_flag = True
                check_file_list.append(file_name)
                logging.error('the file {} does not existed'.format(file_name))
        if check_again_flag:
            loop_count = loop_count + 1
            time.sleep(10 * loop_count)
            if loop_count > 3:
                logging.error('the files {} load failed'.format(check_file_list))
                return
            self.check_files_ready(file_path, check_file_list, loop_count)

    def load_pickle(self, file):
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = pickle.load(infile)
            infile.close()
            return dict
        else:
            return {}

    def load_json(self, file):
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = json.load(infile)
            infile.close()
            return dict
        else:
            return {}

    def Status(self, request, context):
        logging.info('Status(self, request, context)...')
        status = Any()
        status.value =  json.dumps({
            "redis_status": rCache.connection_status(),
            "last_filter_result": localtime
        }).encode('utf-8')
        statusResponse = service_pb2.StatusResponse(code=0)
        statusResponse.status.Pack(status)
        return statusResponse  

    def Stop(self, request, context):
        logging.info('Stop(self, request, context)...')
        logging.info('Recieved singal -> %d', request.signal)
        commonResponse = service_pb2.CommonResponse(code=0, description='stop with doing nothing')
        return commonResponse 

    def GetRecommendData(self, request, context):
        logging.info('GetRecommendData start')

        # Retrieve request data        
        request_body = Any()
        request.requestBody.Unpack(request_body)
        reqData = json.loads(request_body.value, encoding='utf-8')
        user_id = reqData['user_id']
        recommend_type = reqData['recommend_type']
        logging.info('user_id -> {}'.format(user_id))
        logging.info('recommend_type -> {}'.format(recommend_type))

        recommend_result = self.get_recommend_result(user_id, recommend_type)

        logging.info("recommend result {}".format(recommend_result))

        getRecommendDataResponseValue = {
            'data': recommend_result
        }

        getRecommendataResponseAny = Any()
        getRecommendataResponseAny.value =  json.dumps(getRecommendDataResponseValue).encode('utf-8')
        getRecommendDataResponse = service_pb2.GetRecommendDataResponse(code=0, description='retrieve data with success')
        getRecommendDataResponse.results.Pack(getRecommendataResponseAny)        

        logging.info("get recommend data complete") 
        return getRecommendDataResponse

    def GetPsRecommendData(self, request, context):
        logging.info('GetPsRecommendData start')

        # Retrieve request data
        request_body = Any()
        request.requestBody.Unpack(request_body)
        reqData = json.loads(request_body.value, encoding='utf-8')
        user_id = reqData['user_id']
        recommend_type = reqData['recommend_type']
        logging.info('user_id -> {}'.format(user_id))
        logging.info('recommend_type -> {}'.format(recommend_type))

        ps_recommend_result = self.get_ps_recommend_result(user_id, recommend_type)

        logging.info("personalize recommend result {}".format(ps_recommend_result))

        getPsRecommendDataResponseValue = {
            'data': ps_recommend_result
        }

        getPsRecommendataResponseAny = Any()
        getPsRecommendataResponseAny.value = json.dumps(getPsRecommendDataResponseValue).encode('utf-8')
        getPsRecommendDataResponse = service_pb2.GetPsRecommendDataResponse(code=0,
                                                                        description='retrieve data with success')
        getPsRecommendDataResponse.results.Pack(getPsRecommendataResponseAny)

        logging.info("get recommend data complete")
        return getPsRecommendDataResponse

    def get_recommend_result(self, user_id, recommend_type):
        logging.info('get_recommend_result start!!')
        recommend_list = []
        if recommend_type == 'recommend':
            logging.info('recommend movie list to user')
            # get filtered data from filter redis cache
            filtered_data = []
            filtered_data_redis = rCache.get_data_from_hash(user_id_filter_dict, user_id)
            if filtered_data_redis:
                # [{timestamp: [{"6554153017963184647": "recommend"}...]}, {timestamp: [{"6554153017963184647": "recommend"}...]}]
                filtered_data = json.loads(filtered_data_redis, encoding='utf-8')
            else:
                # TODO coldstar data
                logging.info('start coldstart process!')
                filtered_data = self.generate_cold_start_data(user_id)

            logging.info('filtered_data {}'.format(filtered_data))
            # generate new recommend data, store them into cache
            recommend_list = self.generate_new_recommend_data(user_id, filtered_data)
            logging.info('recommend_list {}'.format(recommend_list))
        else:
            logging.info('get movie list by movie type {}'.format(recommend_type))
            if recommend_type not in self.lCfgCompleteType:
                return recommend_list           
            logging.info('Get movie_category_movie_ids_dict completed')
            if not bool(self.movie_category_movie_ids_dict):
                recommend_list
            movie_id_list = self.movie_category_movie_ids_dict[recommend_type]
            recommend_list = self.generate_movie_list_by_type(movie_id_list)

        return recommend_list

    def get_ps_recommend_result(self, user_id, recommend_type):
        logging.info('get_ps_recommend_result start!!')
        ps_recommend_list = []
        if recommend_type == 'recommend':
            logging.info('personalize recommend movie list to user')
            # get personalize data from filter redis cache
            # personalize_data_redis = rCache.get_data_from_hash(user_id_personalize_dict, user_id)
            # if personalize_data_redis:
            #     # [{timestamp: [{"6554153017963184647": "recommend"}...]}, {timestamp: [{"6554153017963184647": "recommend"}...]}]
            #     personalize_data = json.loads(personalize_data_redis, encoding='utf-8')
            # else:
            #     # TODO coldstar data
            #     logging.info('start coldstart process!')
            #     personalize_data = self.generate_ps_cold_start_data(user_id)
            #
            # logging.info('personalize_data {}'.format(personalize_data))
            # # generate new personalize recommend data, store them into cache
            # ps_recommend_list = self.generate_new_ps_recommend_data(user_id, personalize_data)
            ps_recommend_list = self.get_ps_recommend_list(user_id)
            logging.info('ps_recommend_list {}'.format(ps_recommend_list))
        else:
            logging.info('get movie list by movie type {}'.format(recommend_type))
            if recommend_type not in self.lCfgCompleteType:
                return ps_recommend_list
            logging.info('Get movie_category_movie_ids_dict completed')
            if not bool(self.movie_category_movie_ids_dict):
                ps_recommend_list
            movie_id_list = self.movie_category_movie_ids_dict[recommend_type]
            ps_recommend_list = self.generate_movie_list_by_type(movie_id_list)
        logging.info("get_ps_recommend_result return ps_recommend_list size: {}".format(len(ps_recommend_list)))
        return ps_recommend_list

    def get_ps_recommend_list(self, user_id):
        logging.info("start get recommend list from Personalize for user: {}".format(user_id))
        self.personalize_runtime = boto3.client('personalize-runtime', MANDATORY_ENV_VARS['AWS_REGION'])
        recommend_result = []
        # trigger personalize api
        get_recommendations_response = self.personalize_runtime.get_recommendations(
            campaignArn=self.ps_config['CampaignArn'],
            userId=str(user_id),
        )
        result_list = get_recommendations_response['itemList']
        for item in result_list:
            recommend_result.append({
                "id": item['itemId'],
                "description": 'ps-complete|{}'.format(str(item['score'])),
                "tag": 'recommend'
            })
        logging.info('personalize recommend list {}'.format(recommend_result))
        return recommend_result

    def generate_cold_start_data(self, user_id):
        logging.info('start cold start algorithm')           
        coldstart_item_list = {}
        new_filter_record = []
        i = 0
        while len(coldstart_item_list) < int(MANDATORY_ENV_VARS['COLDSTART_MOVIE_COUNT']):
            index = i % len(self.lCfgCompleteType)
            temp_item_id = self.sample_by_type(self.lCfgCompleteType[index])
            if temp_item_id == None:
                logging.info('Cannot get item id')
                return []
            logging.info('get sample item id {} by type {}'.format(temp_item_id, self.lCfgCompleteType[index]))
            if temp_item_id not in coldstart_item_list:
                desp = [str(temp_item_id), tColdstart, 0, str(self.lCfgCompleteType[index])]
                coldstart_item_list[str(temp_item_id)] = desp

            i = i + 1
        new_filter_record.append({
            calendar.timegm(time.gmtime()): coldstart_item_list
        })

        logging.info('coldstart filter record {}'.format(new_filter_record))
            
        if rCache.load_data_into_hash(user_id_filter_dict, user_id, json.dumps(new_filter_record).encode('utf-8')):
            logging.info('Save filter data into Redis with key : %s ', user_id) 
        return new_filter_record


    def generate_movie_list_by_type(self, movie_id_list):
        movie_recommend_list = []
        count = 0
        present_recommend_movie_id_list = []
        try_count = 0
        need_count = int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT'])
        while count < need_count:
            movie, movie_id = self.get_random_movie(movie_id_list)
            try_count = try_count + 1
            if movie_id not in present_recommend_movie_id_list:
                movie_recommend_list.append(movie)
                present_recommend_movie_id_list.append(movie_id)
                count = count + 1
            if try_count > need_count * 3:
                logging.error(
                    "fail to find enough candidate in generate_movie_list_by_type, need to find {} but only find {}".format(need_count,
                                                                                                    count))
                break
        return movie_recommend_list 

    def get_random_movie(self, movie_id_list):
        logging.info('get_random_movie_id start')
        index = random.randint(0,len(movie_id_list) -1)
        return {
            'id': movie_id_list[index],
            'tag': 'type',
            'description': 'get the list of type'
        }, movie_id_list[index]                

    def generate_new_recommend_data(self, user_id, filtered_data):
        logging.info('generate_new_recommend_data start')

        new_recommend_list = []
        # iterate filter data and get recommend 
        if self.is_cold_start_data(filtered_data):
            logging.info('is cold start data')
            # new_recommend_list: [{'id':'news_id1', 'tag': 'recommend'},{'id':'news_id2', 'tag': 'recommend'}]
            # present_recommend_news_id_list: ['news_id1','news_id2']
            new_recommend_list = self.get_present_recommend_movie_list(filtered_data)
        else:
            hot_topic_count = hot_topic_count_array[random.randint(0,len(hot_topic_count_array) -1)]
            new_recommend_list = self.get_present_recommend_movie_list(filtered_data)
            logging.info('need hot topic movie')
            hot_topic_movie_list = []
            # comment for dev workshop
            hot_topic_movie_list = self.get_hot_topic_movie_list(user_id, hot_topic_count)
            new_recommend_list = hot_topic_movie_list + new_recommend_list

        return new_recommend_list 

    def is_cold_start_data(self, filtered_data):
        for element in filtered_data:
            logging.info('filtered_data element {}'.format(element))
            # k is timestamp
            # v is result
            for k, v in element.items():
                for item_id, item_content in v.items():
                    logging.info('filtered_data first item recommend type {}'.format(item_content[1]))
                    if item_content[1] == tColdstart:
                        return True
                    else:
                        return False   

    def get_present_recommend_movie_list(self, filtered_data):
        item_recommend_list = [] #[{'id':'news_id1', 'tag': 'recommend'},{'id':'news_id2', 'tag': 'recommend'}]
        # each element is filter result associated with a timestamp
        for element in filtered_data:
            # k is timestamp
            # v is result
            for k, v in element.items():
                for item_id, item_content in v.items(): 
                    item_recommend_list.append({
                        'id': item_id,
                        'tag': item_content[1],
                        'description': item_content[3]
                    })
        return item_recommend_list      

    def get_hot_topic_movie_list(self, user_id, hot_topic_count):
        movie_list = []
        hot_topic_type = self.get_hot_topic_type(user_id)
        if hot_topic_type == '':
            return []
        count = 0
        index = 0
        while count < hot_topic_count:
            movie_id = self.get_hot_topic_item(hot_topic_type[0], index)
            if movie_id == '':
                return movie_list
            index = index + 1                
            logging.info("get hot topic movie id {}".format(movie_id))
            movie_list.append({
                'id': movie_id,
                'tag': tRecommend,
                'description': "online_hot_topic|{}".format(hot_topic_type[0])
            })
            count = count + 1
        logging.info('hot topic list {}'.format(movie_list))
        return movie_list

    def get_hot_topic_type(self, user_id):
        httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
        if httpResp.status_code != 200:
            return ''
        user_portrait = httpResp.json()
        logging.info('user_portrait: {}'.format(user_portrait))

        user_portrait_result = user_portrait['results']

        sort_type = []
        for item_type, kwsc in user_portrait_result['category'].items():
            if item_type != 'recent':
                sort_type.append((item_type, kwsc['score']))
        sort_type.sort(key = lambda x: x[1], reverse = True)
        logging.info('sort_type {}'.format(sort_type))

        hot_topic_type = sort_type[0]
        logging.info('hot_topic_type {}'.format(hot_topic_type))
        return hot_topic_type               

    def sample_by_type(self, item_type):
        logging.info('sample_by_type start, type {}'.format(item_type))
        if not bool(self.movie_category_movie_ids_dict):
            logging.info('movie_category_movie_ids_dict is empty')
            return None
        movie_id_list_by_category = self.movie_category_movie_ids_dict[item_type]

        index = random.randint(0,len(movie_id_list_by_category) -1)
        return movie_id_list_by_category[index] 
 
    def get_hot_topic_item(self, item_type, index):
        logging.info('get_hot_topic_item start, type {}'.format(item_type))
        if not bool(self.movie_category_movie_ids_dict):
            logging.info('movie_category_movie_ids_dict is empty')
            return ''
        movie_id_list_by_category = self.movie_category_movie_ids_dict[item_type]            
        if index < 0 or index >= len(movie_id_list_by_category):
            logging.info('index is not in the range of movie_id_list_by_category {}'.format(movie_id_list_by_category))
            return ''
        return movie_id_list_by_category[index]                           

def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var]=os.environ.get(var)
    
    # Initial redis connection
    global rCache
    rCache = cache.RedisCache(host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])

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
    print('retrieve plugin start')
    init()
    serve(os.environ.get("PLUGIN_NAME", "default"))