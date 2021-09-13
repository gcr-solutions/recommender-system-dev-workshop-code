from concurrent import futures
import logging
import os
import json
from datetime import datetime
import pickle
import requests
import calendar;
import time
import random
from random import sample
import sys

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
    'AWS_REGION': 'ap-northeast-1',

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,

    'FILTER_CONFIG': 'filter_config.pickle',
    'MOVIE_ID_MOVIE_PROPERTY': 'movie_id_movie_property_dict.pickle',
    'MOVIE_CATEGORY_MOVIE_IDS': 'movie_category_movie_ids_dict.pickle',
    'FILTER_BATCH_RESULT': 'filter_batch_result.pickle',
    'N_DIVERSITY': 4,
    'N_FILTER': 20,
    'RANK_THRESHOLD': 0.5, 
    'COLDSTART_NEWS_COUNT': 100,
    'RECOMMEND_ITEM_COUNT': 20,
    'DUPLICATE_INTERVAL': 10, #min
    'PORTRAIT_SERVICE_ENDPOINT': 'http://portrait:5300'
}

user_id_filter_dict='user_id_filter_dict'
user_id_recommended_dict='user_id_recommended_dict'

tRecommend = 'recommend'
tDiversity = 'diversity'
tColdstart = 'coldstart'
# lCfgCompleteType = ['item_story', 'item_culture', 'item_entertainment', 'item_sports', 'item_finance', 'item_house', 'item_car', 'item_edu', 'item_tech', 'item_military', 'item_travel', 'item_world', 'stock', 'item_agriculture', 'item_game']
lCfgFilterType = ['item_game']
hot_topic_count_array = [2,3]
pickle_type = 'inverted-list'

# lastUpdate
localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

class Filter(service_pb2_grpc.FilterServicer):

    def __init__(self):
        logging.info('__init__(self)...')
        # TODO load data for filter, get parameters from stream
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        config_file_list = []
        config_file_list.append(MANDATORY_ENV_VARS['FILTER_CONFIG'])
        self.reload_pickle_type(local_data_folder, config_file_list)

        pickle_file_list = []
        pickle_file_list.append(MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_PROPERTY'])
        pickle_file_list.append(MANDATORY_ENV_VARS['MOVIE_CATEGORY_MOVIE_IDS'])
        pickle_file_list.append(MANDATORY_ENV_VARS['FILTER_BATCH_RESULT'])
        self.reload_pickle_type(local_data_folder, pickle_file_list)

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
            self.reload_pickle_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        logging.info('Re-initial filter service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse 

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

    def reload_pickle_type(self, file_path, file_list):
        logging.info('reload_pickle_type  strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))                 
            if MANDATORY_ENV_VARS['FILTER_BATCH_RESULT'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload filter_batch_result file {}'.format(pickle_path))
                    self.filter_batch_result= self.load_pickle(pickle_path) 
                    # load filter result into redis
                    for user_id, filter_batch in self.filter_batch_result.items():
                        existed_filter_record = []
                        existed_filter_record_redis = rCache.get_data_from_hash(user_id_filter_dict, user_id)
                        if user_id == '13518':
                            logging.info('!!!!!!!!!existed_filter_record {}'.format(existed_filter_record_redis))
                        existed_filter_record = []
                        # check if there is coldstart data, remove them:
                        if existed_filter_record_redis:
                            existed_filter_record = json.loads(existed_filter_record_redis, encoding='utf-8')
                            for k,v in existed_filter_record[0].items():
                                if user_id == '13518':
                                    logging.info('!!!!!!!!existed_filter_record first element {}'.format(v))
                                for k1, v1 in v.items():
                                    if v1[1] == tColdstart:
                                        logging.info('there is coldstart data, clear them')
                                        existed_filter_record = []
                                        break
                        existed_filter_record.insert(0, {calendar.timegm(time.gmtime()): filter_batch})
                        if rCache.load_data_into_hash(user_id_filter_dict, user_id, json.dumps(existed_filter_record).encode('utf-8')):
                            if user_id == '13518':
                                logging.info('Batch Save filter data into Redis with key : %s ', user_id)
                else:
                    logging.info('reload filter_batch_result, file is empty')         
            elif MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_PROPERTY'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload movie_id_movie_property file {}'.format(pickle_path))
                    self.movie_id_movie_property_dict= self.load_pickle(pickle_path) 
                else:
                    logging.info('reload movie_id_movie_property, file is empty')         
            elif MANDATORY_ENV_VARS['MOVIE_CATEGORY_MOVIE_IDS'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload movie_category_movie_id file {}'.format(pickle_path))
                    self.movie_category_movie_ids_dict= self.load_pickle(pickle_path) 
                    self.lCfgCompleteType = list(self.movie_category_movie_ids_dict.keys())
                else:
                    logging.info('reload movie_category_movie_id, file is empty')         
            elif MANDATORY_ENV_VARS['FILTER_CONFIG'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload filter_config file {}'.format(pickle_path))
                    self.filter_config = self.load_pickle(pickle_path) 
                else:
                    logging.info('reload filter_config, file is empty')         

    def load_pickle(self, file):
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = pickle.load(infile)
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

    def FilterProcess(self, request, context):
        logging.info('filter_process start')

        requestMessage = Any()
        request.dicts.Unpack(requestMessage)
        logging.info('Recieved notice requestMessage -> {}'.format(requestMessage))
        requestMessageJson = json.loads(requestMessage.value, encoding='utf-8')
        # Retrieve request data        
        user_id = requestMessageJson['user_id']
        rank_result = requestMessageJson['rank_result']['rank_result']
        recall_result = requestMessageJson['recall_result']
        logging.info('user_id -> {}'.format(user_id))
        logging.info('rank_result -> {}'.format(rank_result))
        logging.info('recall_result -> {}'.format(recall_result))
        recall_result_dict = {}
        recall_result_dict[str(user_id)] = recall_result

        filter_result = self.generate_filter_result(user_id, recall_result_dict, rank_result)

        filterProcessResponseValue = {
            'user_id': user_id,
            'filter_result': filter_result
        }

        filterProcessResponseAny = Any()
        filterProcessResponseAny.value =  json.dumps(filterProcessResponseValue).encode('utf-8')
        filterProcessResponse = service_pb2.FilterProcessResponse(code=0, description='rank process with success')
        filterProcessResponse.results.Pack(filterProcessResponseAny)        

        logging.info("filter process complete") 
        return filterProcessResponse

    def GetFilterData(self, request, context):
        logging.info('GetFilterData start')

        # Retrieve request data        
        request_body = Any()
        request.requestBody.Unpack(request_body)
        reqData = json.loads(request_body.value, encoding='utf-8')
        user_id = reqData['user_id']
        recommend_type = reqData['recommend_type']
        logging.info('user_id -> {}'.format(user_id))
        logging.info('recommend_type -> {}'.format(recommend_type))

        recommend_result = self.get_filter_recommend_result(user_id, recommend_type)

        logging.info("recommend result {}".format(recommend_result))

        getFilterDataResponseValue = {
            'data': recommend_result
        }

        getFilterDataResponseAny = Any()
        getFilterDataResponseAny.value =  json.dumps(getFilterDataResponseValue).encode('utf-8')
        getFilterDataResponse = service_pb2.GetFilterDataResponse(code=0, description='rank process with success')
        getFilterDataResponse.results.Pack(getFilterDataResponseAny)        

        logging.info("get filter data complete") 
        return getFilterDataResponse 

    def get_filter_recommend_result(self, user_id, recommend_type):
        recommend_list = []
        if recommend_type == 'recommend':
                logging.info('recommend item list to user')
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
            logging.info('get item list by item type {}'.format(recommend_type))
            if recommend_type not in self.lCfgCompleteType:
                return recommend_list
            logging.info('Get movie_category_movie_ids_dict completed')
            if not bool(self.movie_category_movie_ids_dict):
                recommend_list
            item_id_list = self.movie_category_movie_ids_dict[recommend_type]
            recommend_list = self.generate_item_list_by_type(item_id_list)

        return recommend_list

    def generate_cold_start_data(self, user_id):
        logging.info('start cold start algorithm')           
        coldstart_item_list = {}
        new_filter_record = []
        i = 0
        while len(coldstart_item_list) < int(MANDATORY_ENV_VARS['COLDSTART_NEWS_COUNT']):
            index = i % len(self.lCfgCompleteType)
            temp_item_id = self.sample_by_type(self.lCfgCompleteType[index], 'generate_cold_start_data')
            if temp_item_id == None:
                logging.info('Cannot get item id')
                return []
            logging.info('get sample item id {} by type {}'.format(temp_item_id, self.lCfgCompleteType[index]))
            if temp_item_id not in coldstart_item_list:
                desp = [str(temp_item_id), tColdstart, 0, str(self.lCfgCompleteType[index])]
                coldstart_item_list[str(temp_item_id)] = desp
                # coldstart_item_list.append({
                #     str(temp_item_id) : desp
                # })
            i = i + 1
        new_filter_record.append({
            calendar.timegm(time.gmtime()): coldstart_item_list
        })

        logging.info('coldstart filter record {}'.format(new_filter_record))
            
        if rCache.load_data_into_hash(user_id_filter_dict, user_id, json.dumps(new_filter_record).encode('utf-8')):
            logging.info('Save filter data into Redis with key : %s ', user_id) 
        return new_filter_record                   


    def generate_item_list_by_type(self, item_id_list):
        item_recommend_list = []
        count = 0
        present_recommend_item_id_list = []
        need_count = int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT'])
        try_count = 0
        while count < int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']):
            item, item_id = self.get_random_item(item_id_list)
            try_count = try_count + 1
            if item_id not in present_recommend_item_id_list:
                item_recommend_list.append(item)
                present_recommend_item_id_list.append(item_id)
                count = count + 1
            if try_count > need_count * 3:
                logging.error(
                    "fail to find enough candidate in generate_news_list_by_type, need to find {} but only find {}".format(need_count,
                                                                                                    count))
                break                

        return item_recommend_list 

    def get_random_item(self, item_id_list):
        logging.info('get_random_item_id start')
        index = random.randint(0,len(item_id_list) -1)
        return {
            'id': item_id_list[index],
            'tag': 'type',
            'description': 'get the list of type'
        }, item_id_list[index]                

    def generate_new_recommend_data(self, user_id, filtered_data):
        logging.info('generate_new_recommend_data start')
        # get old recommended data
        # [{timestamp1: [item_id1, item_id2]}, {timestamp2: [item_id1, item_id2]}]  
        recommended_data = self.get_recommended_data(user_id)

        # [item_id1, item_id2]
        recommended_item_list = self.get_recommended_item_id_list(recommended_data)

        new_recommend_list = []
        present_recommend_item_id_list = []
        # iterate filter data and get recommend 
        if self.is_cold_start_data(filtered_data):
            logging.info('is cold start data')
            # new_recommend_list: [{'id':'item_id1', 'tag': 'recommend'},{'id':'item_id2', 'tag': 'recommend'}]
            # present_recommend_item_id_list: ['item_id1','item_id2']
            new_recommend_list, present_recommend_item_id_list, remain_count = self.get_present_recommend_item_list(user_id, filtered_data, recommended_item_list, int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']), True)
        else:
            hot_topic_count = hot_topic_count_array[random.randint(0,len(hot_topic_count_array) -1)]
            new_recommend_list, present_recommend_item_id_list, remain_count = self.get_present_recommend_item_list(user_id, filtered_data, recommended_item_list, int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']) - hot_topic_count, False)
            logging.info('need hot topic item')
            hot_topic_item_list = self.get_hot_topic_item_list(user_id, hot_topic_count, recommended_item_list, present_recommend_item_id_list)
            new_recommend_list = hot_topic_item_list + new_recommend_list

        logging.info('present_recommend_record_list {}'.format(present_recommend_item_id_list))
        recommended_data.append({str(calendar.timegm(time.gmtime())): present_recommend_item_id_list})

        if rCache.load_data_into_hash(user_id_recommended_dict, user_id, json.dumps(recommended_data).encode('utf-8')):
            logging.info('Save user_id_recommended_dict with key : %s ', user_id)

        return new_recommend_list 

    def get_recommended_data(self, user_id):
        recommended_data_redis = rCache.get_data_from_hash(user_id_recommended_dict, user_id)
        recommended_data = []
        if recommended_data_redis:
            recommended_data = json.loads(recommended_data_redis, encoding='utf-8')
            # remove the expired recommended data
            expire_timestamp = calendar.timegm(time.gmtime())/60 - int(MANDATORY_ENV_VARS['DUPLICATE_INTERVAL'])
            for element in recommended_data:
                for k, v in element.items():
                    recommended_time_min = int(k)
                    if expire_timestamp > recommended_time_min/60:
                        recommended_data.remove(element)
        logging.info('recommended_data {} for user {}'.format(recommended_data, user_id))    
        return recommended_data 

    def get_recommended_item_id_list(self, recommended_data):
        # create existed recommended item list, it need to be used later to check duplication item id
        recommended_item_list = []
        for element in recommended_data:
            for k, v in element.items():
                for item_id in v:
                    recommended_item_list.append(item_id) 
        return recommended_item_list 

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
        return False  

    def get_present_recommend_item_list(self, user_id, filtered_data, recommended_item_list, item_list_count, isColdStart):
        item_recommend_list = [] #[{'id':'item_id1', 'tag': 'recommend'},{'id':'item_id2', 'tag': 'recommend'}]
        present_recommend_item_id_list = [] #['item_id1','item_id2']
        recommend_count = 0
        remain_count = 0
        # each element is filter result associated with a timestamp
        for element in filtered_data:
            # k is timestamp
            # v is result
            for k, v in element.items():
                for item_id, item_content in v.items(): 
                    if item_id not in recommended_item_list and item_id not in present_recommend_item_id_list:
                        if recommend_count < item_list_count:
                            item_recommend_list.append({
                                'id': item_id,
                                'tag': item_content[1],
                                'description': item_content[3]
                            }) 
                            present_recommend_item_id_list.append(item_id)
                            recommend_count = recommend_count + 1
                        else:
                            # record the length of remain item list
                            remain_count = remain_count + 1
        item_lacking_count = item_list_count - len(present_recommend_item_id_list)
        if item_lacking_count > 0:
            logging.info('complement item list, count {}'.format(str(item_lacking_count)))
            complement_item_recommend_list = []
            complement_present_recommend_item_id_list = []

            complement_item_recommend_list, complement_present_recommend_item_id_list = self.get_complement_item_recommend_list(user_id, present_recommend_item_id_list, item_lacking_count, isColdStart)
            item_recommend_list = item_recommend_list + complement_item_recommend_list
            present_recommend_item_id_list = present_recommend_item_id_list + complement_present_recommend_item_id_list
        return item_recommend_list, present_recommend_item_id_list, remain_count                                                           

    def get_complement_item_recommend_list(self, user_id, present_recommend_item_id_list, item_lacking_count, isColdStart):
        logging.info('complement_item_recommend_list start')
        complement_item_recommend_list = []
        complement_present_recommend_item_id_list = []
        count = 0

        sort_type = []
        httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
        if httpResp.status_code != 200:
            return complement_item_recommend_list, complement_present_recommend_item_id_list
        user_portrait = httpResp.json()          
         
        logging.info('user_portrait: {}'.format(user_portrait))

        if user_portrait['results'] == {}:
            sort_type = self.lCfgCompleteType
        else:
            sort_type = user_portrait['results']['category']['recent'][0][::-1]
        logging.info('sort_type {}'.format(sort_type))

        while count < item_lacking_count:
            sort_type_count = 0
            try_count = 0
            while sort_type_count < len(sort_type) and count < item_lacking_count:
                try_count = try_count + 1
                item_id = self.sample_by_type(sort_type[sort_type_count], 'get_complement_item_recommend_list')
                if (item_id not in present_recommend_item_id_list and item_id not in complement_present_recommend_item_id_list and item_id != ''):
                    logging.info("get hot topic item id {}".format(item_id))
                    if isColdStart:
                        complement_item_recommend_list.append({
                            'id': item_id,
                            'tag': tColdstart,
                            'description': sort_type[sort_type_count]
                        })
                    else:
                        complement_item_recommend_list.append({
                            'id': item_id,
                            'tag': tRecommend,
                            'description': "online_hot_topic|{}".format(sort_type[sort_type_count])
                        })                        
                    complement_present_recommend_item_id_list.append(item_id)
                    count = count + 1
                    sort_type_count = sort_type_count + 1
                if try_count > 3 * count:
                    logging.error(
                        "fail to find enough candidate, need to find {} but only find {}".format(item_lacking_count,
                                                                                                        count))
                    break                    
            if count < item_lacking_count:    
                diversity_item_id, item_type = self.get_diversity_item_id(present_recommend_item_id_list, complement_present_recommend_item_id_list)
                if diversity_item_id != '':
                    if isColdStart:                        
                        complement_item_recommend_list.append({
                            'id': diversity_item_id,
                            'tag': tColdstart,
                            'description': item_type
                        })
                    else:
                        complement_item_recommend_list.append({
                            'id': diversity_item_id,
                            'tag': tDiversity,
                            'description': "online_hot_topic|Diversity"
                        })                        
                    complement_present_recommend_item_id_list.append(diversity_item_id)
                    count = count + 1

        return complement_item_recommend_list, complement_present_recommend_item_id_list       

    def get_diversity_item_id(self, present_recommend_item_id_list, complement_present_recommend_item_id_list):
        logging.info('get_diversity_item_id start')
        try_count = 0
        while True:
            try_count = try_count + 1
            item_type = self.lCfgCompleteType[random.randint(0,len(self.lCfgCompleteType) -1)]
            item_id = self.sample_by_type(item_type, 'get_diversity_item_id')
            if (item_id not in present_recommend_item_id_list and item_id not in complement_present_recommend_item_id_list and item_id != ''):
                return item_id, item_type
            if try_count > 5:
                return '',''

    def get_hot_topic_item_list(self, user_id, hot_topic_count, recommended_item_list, present_recommend_item_id_list):
        item_list = []
        hot_topic_type = self.get_hot_topic_type(user_id)
        if hot_topic_type == '':
            return []
        count = 0
        while count < hot_topic_count:
            item_id = self.sample_by_type(hot_topic_type[0], 'get_hot_topic_item_list')
            if item_id == '':
                return []
            if item_id not in recommended_item_list and item_id not in present_recommend_item_id_list:                 
                logging.info("get hot topic item id {}".format(item_id))
                item_list.append({
                    'id': item_id,
                    'tag': tRecommend,
                    'description': "online_hot_topic|{}".format(hot_topic_type[0])                   
                })
                count = count + 1

        logging.info('hot topic list {}'.format(item_list))
        return item_list

    def sample_by_type(self, item_type, source):
        logging.info('sample_by_type start, type {}, source {}'.format(item_type, source))
        if not bool(self.movie_category_movie_ids_dict):
            logging.info('movie_category_movie_ids_dict is empty')
            return None
        item_id_list_by_type = self.movie_category_movie_ids_dict[str(item_type)]

        index = random.randint(0,len(item_id_list_by_type) -1)
        return item_id_list_by_type[index]  

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

    def generate_filter_result(self, user_id, recall_result, rank_result):
        logging.info('generate_filter_result start')
           
        logging.info('recall_result: {}'.format(recall_result))
                   
        logging.info('rank_result: {}'.format(rank_result))  

        httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
        if httpResp.status_code != 200:
            return service_pb2.FilterProcessResponse(code=-1, description=('Failed to get portrait for -> {}').format(user_id))
        user_portrait = httpResp.json()          
         
        logging.info('user_portrait: {}'.format(user_portrait))  

        user_portrait_result = user_portrait['results']   
        
        existed_filter_record_redis = rCache.get_data_from_hash(user_id_filter_dict, user_id)
        logging.info('existed_filter_record {}'.format(existed_filter_record_redis))
        existed_filter_record = []
        # check if there is coldstart data, remove them:
        if existed_filter_record_redis:
            existed_filter_record = json.loads(existed_filter_record_redis, encoding='utf-8')
            for k,v in existed_filter_record[0].items():
                logging.info('existed_filter_record first element {}'.format(v))
                for k1, v1 in v.items():
                    logging.info('existed_filter_record first item recommend type {} of user {}'.format(v1, k1))
                    if v1[1] == tColdstart:
                        logging.info('there is coldstart data, clear them')
                        existed_filter_record = []
                        break

        new_filter_record = self.generate_new_filter_record(recall_result, rank_result)
        logging.info('new_filter_record {}'.format(new_filter_record))

        existed_filter_record.insert(0, {calendar.timegm(time.gmtime()): new_filter_record[user_id]})

        if rCache.load_data_into_hash(user_id_filter_dict, user_id, json.dumps(existed_filter_record).encode('utf-8')):
            logging.info('Save filter data into Redis with key : %s ', user_id)
        logging.info('final existed_filter_record {}'.format(existed_filter_record))
        logging.info('filter_process completed')

    def get_dict_pos(self, key, dict_var):
        return list(dict_var.keys()).index(key)

    def calc_filter_score(self, recall_score, rank_score, recall_mt=None, rank_mt=None, recall_pos=None, rank_pos=None):
        filter_score = min(1.0, recall_score / 40.0 + rank_score)
        return round(filter_score, 2)

    def mt_construct(self, timing, mt, pos):
        type_list = []
        type_list.append(str(timing))
        type_list.append(str(mt))
        type_list.append(str(pos))
        type_name = '_'.join(type_list)
        return type_name

    def sort_and_fill_pos(self, filter_result):
        sort_filter_result = dict(
            sorted(filter_result.items(), key=lambda item: item[1][2], reverse=True))
        filter_pos = 0
        update_filter_result = dict()
        for filter_id, filter_content in sort_filter_result.items():
            current_trace = filter_content[3]
            current_trace_split_list = current_trace.split('|')
            current_filter_type = current_trace_split_list[4]
            current_filter_type_split_list = current_filter_type.split('_')
            update_filter_type_split_list = current_filter_type_split_list
            update_filter_type_split_list[2] = str(filter_pos)
            update_filter_type = '_'.join(update_filter_type_split_list)
            update_trace_split_list = current_trace_split_list
            update_trace_split_list[-2] = update_filter_type
            update_trace = '|'.join(update_trace_split_list)
            update_filter_content = filter_content
            update_filter_content[3] = update_trace
            #         print("update id {} trace {} type {}".format(filter_id, update_trace,update_filter_type_split_list))
            update_filter_result[str(filter_id)] = update_filter_content
            # update filter pos
            filter_pos = filter_pos + 1

    def initial_diversity(self, stats_result, filter_config):
        for cate in filter_config['category']:
            stats_result[cate] = 0

    def category_diversity_logic(self, filter_result, stats_result, dict_category_id, filter_config):
        diversity_count = filter_config['category_diversity_count']
        min_category = None
        min_category_count = 999
        candidate_category_list = []
        for cate, count in stats_result.items():
            if count < min_category_count and count != 0:
                min_category_count = count
                min_category = cate
            elif count == 0:
                candidate_category_list.append(cate)
        if min_category != None:
            candidate_category_list.append(min_category)
        diversity_result_list = []
        diversity_result_content_list = []
        current_diversity_count = 0

        filter_result_list = list(filter_result.keys())
        filter_result_content_list = list(filter_result.values())
        sample_try = 0
        catch_count = 0
        while catch_count < diversity_count:
            for cate in candidate_category_list:
                sample_try = sample_try + 1
                candidate_id = sample(dict_category_id[str(cate)], 1)[0]
                if candidate_id in filter_result_list:
                    continue
                else:
                    filter_result_list.append(str(candidate_id))
                    filter_result_content_list.append([str(candidate_id), tDiversity, 0.0,
                                                    'online_diversity_{}|{}'.format(len(filter_result_list), cate)])
                    catch_count = catch_count + 1
                    if catch_count >= diversity_count:
                        break
            if sample_try > 5 * diversity_count:
                logging.error(
                    "fail to find enough diversity candidate, need to find {} but only find {}".format(diversity_count,
                                                                                                    catch_count + 1))
                break

        update_filter_result = dict(zip(filter_result_list, filter_result_content_list))
        return update_filter_result

    def generate_new_filter_record(self, dict_recall_result, dict_rank_result):
        # 同一批次去重/统计
        # 运行时机
        run_timing = 'online'
        dict_filter_result = {}
        for user_id, recall_result in dict_recall_result.items():
            #     print("user id {}".format(user_id))
            current_user_result = {}
            current_diversity_result = {}
            self.initial_diversity(current_diversity_result, self.filter_config)
            for recall_id, recall_property in recall_result.items():
                #         print("item id {}".format(recall_id))
                # 构建recall_type
                recall_type = self.mt_construct(run_timing, recall_property[1], recall_property[2])
                # 构建recall_score
                recall_score = round(recall_property[3], 2)
                # 构建rank_type
                rank_pos = str(self.get_dict_pos(str(recall_id), dict_rank_result[str(user_id)]))
                rank_type = self.mt_construct(run_timing, 'deepfm', rank_pos)
                # 构建rank_score
                rank_score = round(dict_rank_result[str(user_id)][str(recall_id)], 2)
                # 构建filter_type
                filter_type = self.mt_construct(run_timing, tRecommend, 'TBD')
                # 构建filter_score
                filter_score = self.calc_filter_score(recall_score, rank_score)
                #         print("{}|{}|{}|{}|{}|{}".format(recall_type,recall_score,rank_type,rank_score))
                #         break
                recommend_trace = "{}|{}|{}|{}|{}|{}".format(recall_type, recall_score, rank_type, rank_score, filter_type,
                                                            filter_score)
                current_user_result[str(recall_id)] = []
                current_user_result[str(recall_id)].append(str(recall_id))
                current_user_result[str(recall_id)].append(tRecommend)
                current_user_result[str(recall_id)].append(filter_score)
                current_user_result[str(recall_id)].append(recommend_trace)
                # 更新多样性统计
                current_category = self.movie_id_movie_property_dict[str(recall_id)]['category']
                for cate in current_category:
                    if cate is not None:
                        current_diversity_result[cate] = current_diversity_result[cate] + 1
            # 根据filter score更新排序
            self.sort_and_fill_pos(current_user_result)
            update_user_result = self.category_diversity_logic(current_user_result, current_diversity_result, self.movie_category_movie_ids_dict,
                                                        self.filter_config)
            dict_filter_result[str(user_id)] = update_user_result
        return dict_filter_result

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
    service_pb2_grpc.add_FilterServicer_to_server(Filter(), server)
    SERVICE_NAMES = (
        service_pb2.DESCRIPTOR.services_by_name['Filter'].full_name,
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
    print('filter plugin start')
    init()
    serve(os.environ.get("PLUGIN_NAME", "default"))