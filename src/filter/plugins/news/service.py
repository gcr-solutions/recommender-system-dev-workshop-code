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

    'NEWS_ID_PROPERTY': 'news_id_news_property_dict.pickle',
    'NEWS_TYPE_NEWS_IDS': 'news_type_news_ids_dict.pickle',
    'FILTER_CONFIG': 'filter_config.pickle',
    'FILTER_BATCH_RESULT': 'filter_batch_result.pickle',

    'N_DIVERSITY': 4,
    'N_FILTER': 20,
    'RANK_THRESHOLD': 0.5, 
    'COLDSTART_NEWS_COUNT': 100,
    'RECOMMEND_ITEM_COUNT': 20,
    'DUPLICATE_INTERVAL': 10, #min
    'PORTRAIT_SERVICE_ENDPOINT': 'http://portrait:5300',
    'RANK_MODEL': 'dkn'

}

user_id_filter_dict='user_id_filter_dict'
user_id_recommended_dict='user_id_recommended_dict'

tRecommend = 'recommend'
tDiversity = 'diversity'
tColdstart = 'coldstart'
lCfgCompleteType = ['news_story', 'news_culture', 'news_entertainment', 'news_sports', 'news_finance', 'news_house', 'news_car', 'news_edu', 'news_tech', 'news_military', 'news_travel', 'news_world', 'stock', 'news_agriculture', 'news_game']
lCfgFilterType = ['news_game']
hot_topic_count_array = [2,3]
pickle_type = 'inverted-list'

# lastUpdate
localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

class Filter(service_pb2_grpc.FilterServicer):

    def __init__(self):
        logging.info('__init__(self)...')
        # TODO load data for filter, get parameters from stream
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        file_list = [MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS']]
        file_list.append(MANDATORY_ENV_VARS['NEWS_ID_PROPERTY'])
        file_list.append(MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'])
        file_list.append(MANDATORY_ENV_VARS['FILTER_BATCH_RESULT'])
        file_list.append(MANDATORY_ENV_VARS['FILTER_CONFIG'])

        self.reload_pickle_type(local_data_folder, file_list, False)

    def Reload(self, request, context):
        logging.info('Restart(self, request, context)...')
        requestMessage = Any()
        request.dicts.Unpack(requestMessage)
        logging.info('Recieved notice requestMessage -> {}'.format(requestMessage))
        requestMessageJson = json.loads(requestMessage.value, encoding='utf-8')
        file_type = requestMessageJson['file_type']
        file_list = eval(requestMessageJson['file_list'])
        logging.info('file_type -> {}'.format(file_type))
    #    logging.info('file_list -> {}'.format(file_list)) 

        self.check_files_ready(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list, 0)
        if file_type == pickle_type:
            self.reload_pickle_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list, True)
        logging.info('Re-initial filter service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse 

    def reload_pickle_type(self, file_path, file_list, reloadFlag):
        logging.info('reload_pickle_type strat')
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
                        # check if there is coldstart data, remove them:
                        if existed_filter_record_redis:
                            existed_filter_record = json.loads(existed_filter_record_redis, encoding='utf-8')
                            for k,v in existed_filter_record[0].items():
                                for k1, v1 in v.items():
                                    if v1[1] == tColdstart:
                                        logging.info('there is coldstart data, clear them')
                                        existed_filter_record = []
                                        break
                        existed_filter_record.insert(0, {calendar.timegm(time.gmtime()): filter_batch})

            elif MANDATORY_ENV_VARS['NEWS_ID_PROPERTY'] in pickle_path:
                logging.info('reload news_id_news_property_dict file {}'.format(pickle_path))
                self.news_id_news_property_dict = self.load_pickle(pickle_path)
            elif MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'] in pickle_path:
                logging.info('reload news_type_news_ids_dict file {}'.format(pickle_path))
                self.news_type_news_ids_dict = self.load_pickle(pickle_path) 
                self.lCfgCompleteType = list(self.news_type_news_ids_dict.keys())
            elif MANDATORY_ENV_VARS['FILTER_CONFIG'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload filter_config file {}'.format(pickle_path))
                    self.filter_config = self.load_pickle(pickle_path) 
                    logging.info('filter_config is {}'.format(self.filter_config))
                else:
                    logging.info('reload filter_config, file is empty') 

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
        rank_result = requestMessageJson['rank_result']
        recall_result = requestMessageJson['recall_result']
        logging.info('user_id -> {}'.format(user_id))
        logging.info('rank_result -> {}'.format(rank_result))
        logging.info('recall_result -> {}'.format(recall_result))

        filter_result = self.generate_filter_result(user_id, recall_result, rank_result)

        logging.info("filter result {}".format(filter_result))

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
        

        print("---------time before trigger get_filter_recommend_result:")
        print(datetime.now())
    
        recommend_result = self.get_filter_recommend_result(user_id, recommend_type)
        
        print("---------time after trigger get_filter_recommend_result:")
        print(datetime.now())

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
        logging.info('get_filter_recommend_result start!!')
        recommend_list = []
        if recommend_type == 'recommend':
                logging.info('recommend news list to user')
                # get filtered data from filter redis cache
                filtered_data = []
                
                print("---------time before  get_data_from_hash:")
                print(datetime.now())
    
                filtered_data_redis = rCache.get_data_from_hash(user_id_filter_dict, user_id)
                
                print("---------time after  get_data_from_hash:")
                print(datetime.now())
                
                if filtered_data_redis:
                    # [{timestamp: [{"6554153017963184647": "recommend"}...]}, {timestamp: [{"6554153017963184647": "recommend"}...]}]
                    filtered_data = json.loads(filtered_data_redis, encoding='utf-8')
                else:
                    # TODO coldstar data
                    logging.info('start coldstart process!')
                    filtered_data = self.generate_cold_start_data(user_id)

                # logging.info('filtered_data {}'.format(filtered_data))
                # generate new recommend data, store them into cache
                

                recommend_list = self.generate_new_recommend_data(user_id, filtered_data)
                

                # logging.info('recommend_list {}'.format(recommend_list))
        else:
            logging.info('get news list by news type {}'.format(recommend_type))
            if recommend_type not in self.lCfgCompleteType:
                return recommend_list           
            logging.info('Get news_type_news_ids_dict completed')
            if not bool(self.news_type_news_ids_dict):
                recommend_list
            news_id_list = self.news_type_news_ids_dict[recommend_type]
            recommend_list = self.generate_news_list_by_type(news_id_list)

        print("---------time finish get_filter_recommend_result :")
        print(datetime.now())
                
        return recommend_list

    def generate_cold_start_data(self, user_id):
        logging.info('start cold start algorithm')           
        coldstart_item_list = {}
        new_filter_record = []
        i = 0
        while len(coldstart_item_list) < int(MANDATORY_ENV_VARS['COLDSTART_NEWS_COUNT']):
            index = i % len(self.lCfgCompleteType)
            temp_item_id = self.sample_by_type(self.lCfgCompleteType[index])
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

 #       logging.info('coldstart filter record {}'.format(new_filter_record))
            
        if rCache.load_data_into_hash(user_id_filter_dict, user_id, json.dumps(new_filter_record).encode('utf-8')):
            logging.info('Save filter data into Redis with key : %s ', user_id) 
        return new_filter_record            


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

    def generate_new_recommend_data(self, user_id, filtered_data):
        logging.info('generate_new_recommend_data start')
        # get old recommended data
        # [{timestamp1: [news_id1, news_id2]}, {timestamp2: [news_id1, news_id2]}]  
        recommended_data = self.get_recommended_data(user_id)

        # [news_id1, news_id2]
        recommended_news_list = self.get_recommended_news_id_list(recommended_data)

        new_recommend_list = []
        present_recommend_news_id_list = []
        # iterate filter data and get recommend 
        if self.is_cold_start_data(filtered_data):
            logging.info('is cold start data')
            # new_recommend_list: [{'id':'news_id1', 'tag': 'recommend'},{'id':'news_id2', 'tag': 'recommend'}]
            # present_recommend_news_id_list: ['news_id1','news_id2']
            new_recommend_list, present_recommend_news_id_list, remain_count = self.get_present_recommend_news_list(user_id, filtered_data, recommended_news_list, int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']), True)
        else:
            hot_topic_count = hot_topic_count_array[random.randint(0,len(hot_topic_count_array) -1)]
            new_recommend_list, present_recommend_news_id_list, remain_count = self.get_present_recommend_news_list(user_id, filtered_data, recommended_news_list, int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']) - hot_topic_count, False)
            logging.info('need hot topic news')
            hot_topic_news_list = self.get_hot_topic_news_list(user_id, hot_topic_count, present_recommend_news_id_list, recommended_news_list)
            new_recommend_list = hot_topic_news_list + new_recommend_list

    #    logging.info('present_recommend_record_list {}'.format(present_recommend_news_id_list))
        recommended_data.append({str(calendar.timegm(time.gmtime())): present_recommend_news_id_list})

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
  #      logging.info('recommended_data {} for user {}'.format(recommended_data, user_id))    
        return recommended_data 

    def get_recommended_news_id_list(self, recommended_data):
        # create existed recommended news list, it need to be used later to check duplication news id
        recommended_news_list = []
        for element in recommended_data:
            for k, v in element.items():
                for news_id in v:
                    recommended_news_list.append(news_id) 
        return recommended_news_list 

    def is_cold_start_data(self, filtered_data):
        for element in filtered_data:
    #        logging.info('filtered_data element {}'.format(element))
            # k is timestamp
            # v is result
            for k, v in element.items():
                for item_id, item_content in v.items():
    #                logging.info('filtered_data first item recommend type {}'.format(item_content[1]))
                    if item_content[1] == tColdstart:
                        return True
        # for k,v in filtered_data[0].items():
        #     logging.info('filtered_data first element {}'.format(v))
        #     for k1, v1 in v[0].items():
        #         logging.info('filtered_data first news recommend type {}'.format(v1))
        #         if v1 == tColdstart:
        #             return True
        return False  

    def get_present_recommend_news_list(self, user_id, filtered_data, recommended_item_list, item_list_count, isColdStart):
        item_recommend_list = [] #[{'id':'news_id1', 'tag': 'recommend'},{'id':'news_id2', 'tag': 'recommend'}]
        present_recommend_item_id_list = [] #['news_id1','news_id2']
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
   #         logging.info('complement item list, count {}'.format(str(item_lacking_count)))
            complement_item_recommend_list = []
            complement_present_recommend_item_id_list = []

            complement_item_recommend_list, complement_present_recommend_item_id_list = self.get_complement_item_recommend_list(user_id, present_recommend_item_id_list, item_lacking_count, isColdStart)
            item_recommend_list = item_recommend_list + complement_item_recommend_list
            present_recommend_item_id_list = present_recommend_item_id_list + complement_present_recommend_item_id_list
        return item_recommend_list, present_recommend_item_id_list, remain_count                                                           

    def get_complement_item_recommend_list(self, user_id, present_recommend_news_id_list, news_lacking_count, isColdStart):
 #       logging.info('get_complement_item_recommend_list start')
        complement_news_recommend_list = []
        complement_present_recommend_news_id_list = []
        count = 0

        sort_type = []
        httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
        if httpResp.status_code != 200:
            return complement_news_recommend_list, complement_present_recommend_news_id_list
        user_portrait = httpResp.json()          
         
 #       logging.info('user_portrait: {}'.format(user_portrait))
        if user_portrait['results'] == {}:
            sort_type = lCfgCompleteType
        else:
            sort_type = user_portrait['results']['type']['recent'][0][::-1]
 #       logging.info('sort_type {}'.format(sort_type))

        while count < news_lacking_count:
            try_count = 0
            sort_type_count = 0
            while sort_type_count < len(sort_type) and count < news_lacking_count:
                try_count = try_count + 1
                news_id = self.sample_by_type(sort_type[sort_type_count])
                if (news_id not in present_recommend_news_id_list and news_id not in complement_present_recommend_news_id_list and news_id != ''):
      #              logging.info("get hot topic news id {}".format(news_id))
                    if isColdStart:
                        complement_news_recommend_list.append({
                            'id': news_id,
                            'tag': tColdstart,
                            'description': sort_type[sort_type_count]
                        })
                    else:
                        complement_news_recommend_list.append({
                            'id': news_id,
                            'tag': tRecommend,
                            'description': "completion|{}".format(sort_type[sort_type_count])
                        })
                    complement_present_recommend_news_id_list.append(news_id)
                    count = count + 1
                    sort_type_count = sort_type_count + 1
                if try_count > 3 * count:
                    logging.error(
                        "fail to find enough candidate, need to find {} but only find {}".format(news_lacking_count,
                                                                                                        count))
                    break
            if count < news_lacking_count:    
                diversity_news_id, news_type = self.get_diversity_news_id(present_recommend_news_id_list, complement_present_recommend_news_id_list)
                if isColdStart:
                    complement_news_recommend_list.append({
                        'id': diversity_news_id,
                        'tag': tColdstart,
                        'description': news_type
                    })
                else:
                    complement_news_recommend_list.append({
                        'id': diversity_news_id,
                        'tag': tDiversity,
                        'description': "completion|Diversity"
                    })
                complement_present_recommend_news_id_list.append(diversity_news_id)
                count = count + 1
        return complement_news_recommend_list, complement_present_recommend_news_id_list        

    def get_diversity_news_id(self, present_recommend_news_id_list, complement_present_recommend_news_id_list):
        logging.info('get_diversity_news_id start')
        while True:
            news_type = self.lCfgCompleteType[random.randint(0,len(self.lCfgCompleteType) -1)]
            news_id = self.sample_by_type(news_type)
            if (news_id not in present_recommend_news_id_list and news_id not in complement_present_recommend_news_id_list and news_id != ''):
                return news_id, news_type       

    def get_hot_topic_news_list(self, user_id, hot_topic_count, present_recommend_news_id_list, recommended_news_list):
        news_list = []
        hot_topic_type = self.get_hot_topic_type(user_id)
        if hot_topic_type == '':
            return []
        count = 0
        index = 0
        while count < hot_topic_count:
            news_id = self.get_hot_topic_item(hot_topic_type[0], index)
            if news_id == '':
                return news_list
            index = index + 1                
            if news_id not in recommended_news_list and news_id not in present_recommend_news_id_list: 
                logging.info("get hot topic news id {}".format(news_id))
                present_recommend_news_id_list.append(news_id)
                news_list.append({
                    'id': news_id,
                    'tag': tRecommend,
                    'description': "online_hot_topic|{}".format(hot_topic_type[0])
                })
                count = count + 1
        logging.info('hot topic list {}'.format(news_list))
        return news_list

       

    def get_hot_topic_type(self, user_id):
        httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
        if httpResp.status_code != 200:
            return ''
        user_portrait = httpResp.json()
        logging.info('user_portrait: {}'.format(user_portrait))

        user_portrait_result = user_portrait['results']

        sort_type = []
        for item_type, kwsc in user_portrait_result['type'].items():
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

        new_filter_record = self.generate_new_filter_record({str(user_id):recall_result}, {str(user_id):rank_result})
        logging.info('new_filter_record {}'.format(new_filter_record))

        existed_filter_record.insert(0, {calendar.timegm(time.gmtime()): new_filter_record[str(user_id)]})

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

    # workflow:
    # analyze user portrait
    # 1. must read type: TopN
    # 2. no longer read type: TopN
    # recommend type
    # 1. filter rank by score - recommend
    # 2. add build dict from last recall result
    #   2.1 multiple shot candidate - recommend
    #   2.2 pick up from diversity type
    # diversity type
    # 1. 
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
                rank_pos = str(self.get_dict_pos(str(recall_id), dict_rank_result[str(user_id)]['data']))
                rank_type = self.mt_construct(run_timing, dict_rank_result[str(user_id)]['model'], rank_pos)
                # 构建rank_score
                rank_score = round(float(dict_rank_result[str(user_id)]['data'][str(recall_id)]), 2)
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
                current_category = self.news_id_news_property_dict[str(recall_id)]['type']
                for cate in current_category:
                    if cate is not None:
                        current_diversity_result[cate] = current_diversity_result[cate] + 1
            # 根据filter score更新排序
            self.sort_and_fill_pos(current_user_result)
            update_user_result = self.category_diversity_logic(current_user_result, current_diversity_result, self.news_type_news_ids_dict,
                                                        self.filter_config)
            dict_filter_result[str(user_id)] = update_user_result
            logging.info("--------------dict_filter_result:{}".format(dict_filter_result))
        return dict_filter_result

    def generate_new_filter_record_old(self, current_filter_record, recall_result, rank_result, user_portrait):
        ndivsersity = int(MANDATORY_ENV_VARS['N_DIVERSITY'])
        # filter number after diversity threshold
        nlocalfilter = int(MANDATORY_ENV_VARS['N_FILTER']) - ndivsersity
        ########################################
        # analyze user portrait
        ########################################
        hot_type, cold_type, filter_type = self.analyze_portrait(user_portrait)
        recall_multiple_id = self.analyze_recall(recall_result)
        logging.info('recall_multiple_id {}'.format(recall_multiple_id))

        # judge cold start logic
        filter_result = []
        filter_id_dict = {}
        ########################################
        # pick up from rank list
        ########################################
        for element in rank_result:
            for item_id, item_score in element.items():
                if float(item_score) > float(MANDATORY_ENV_VARS['RANK_THRESHOLD']):
                    filter_result.append({item_id : tRecommend})
                    filter_id_dict[item_id] = tRecommend
                else:
                    if item_id in recall_multiple_id:
                        filter_result.append({item_id : tRecommend})
                        filter_id_dict[item_id] = tRecommend
        # judge result length
        if len(filter_result) >= nlocalfilter:
            return self.diversity_logic(filter_result[0:nlocalfilter], hot_type, cold_type, filter_type, ndivsersity, filter_id_dict)

        ########################################
        # sample from hot topic
        ########################################
        n = 0
        while len(filter_result) < nlocalfilter:
            pickup_result = self.sample_by_type(hot_type[n%len(hot_type)][0])
            if pickup_result not in filter_id_dict.keys():
                filter_result.append({pickup_result : tRecommend})
            n = n + 1
        
        return self.diversity_logic(filter_result[0:nlocalfilter], hot_type, cold_type, filter_type, ndivsersity, filter_id_dict)                                           

    def analyze_portrait(self, user_portrait):
        # parameters

        nCfgTypeNum = 4
        # user_portrait
        # {'type':score}
        hot_type = []
        cold_type = []
        filter_type = []
        # list to filter
        filter_type = lCfgFilterType
        sort_type = []
        dict_type = {}
        for item_type, kwsc in user_portrait.items():
            sort_type.append((item_type, kwsc['avg']))
            dict_type[item_type] = kwsc['avg']
        sort_type.sort(key = lambda x: x[1], reverse = True)

        if len(sort_type) >= nCfgTypeNum:
            hot_type = sort_type[0:nCfgTypeNum]
        else:
            hot_type = sort_type
        
        for item_type in lCfgCompleteType:
            if item_type not in dict_type.keys():
                cold_type.append(item_type)
        
        if len(cold_type) >= nCfgTypeNum:
            cold_type = cold_type[0:nCfgTypeNum]
        else:
            for idx in range(len(sort_type)):
                if sort_type[-idx-1] != hot_type[-1]:
                    cold_type.append(sort_type[-idx-1])
                if len(cold_type) == nCfgTypeNum:
                    break

        return hot_type, cold_type, filter_type 

    def analyze_recall(self, recall_result):
        item_type_id_dict = {}
        hot_type = []

        for element in recall_result:
            item_id = element[0]
            item_type = element[1]
            if item_type not in item_type_id_dict.keys():
                item_type_id_dict[item_type] = [item_id]
            else:
                current_list = item_type_id_dict[item_type]
                current_list.append(item_id)
                item_type_id_dict[item_type] = current_list
                hot_type.append(item_type)

        hot_list = []
        for item_type in hot_type:
            hot_list = hot_list + item_type_id_dict[item_type]
        
        return hot_list 

    def diversity_logic(self, filter_list, hot_type, cold_type, filter_type, ndivsersity, filter_id_dict):
        # sample cold logic 
        n = 1
        pick_pos = 0
        insert_pos = len(filter_list)/ndivsersity
        # for idx in range(ndivsersity):
        while n <= ndivsersity:
            pickup_result = self.sample_by_type(cold_type[pick_pos%len(cold_type)])
            if pickup_result not in filter_id_dict.keys():
                #filter_list.append({pickup_result : tDiversity})
                filter_list.insert(min(len(pickup_result),int(n*insert_pos)),{pickup_result : tDiversity})
                n = n + 1
            pick_pos = pick_pos + 1
        return filter_list 

    def sample_by_type(self, item_type):
        logging.info('sample_by_type start, type {}'.format(item_type))
        if not bool(self.news_type_news_ids_dict):
            logging.info('news_type_news_ids_dict is empty')
            return None
        # logging.info(news_type_news_ids_dict)
        news_id_list_by_type = self.news_type_news_ids_dict[item_type]

        index = random.randint(0,len(news_id_list_by_type) -1)
        return news_id_list_by_type[index] 
 
    def get_hot_topic_item(self, item_type, index):
        logging.info('get_hot_topic_item start, type {}'.format(item_type))
        if not bool(self.news_type_news_ids_dict):
            logging.info('news_type_news_ids_dict is empty')
            return ''
        news_id_list_by_type = self.news_type_news_ids_dict[item_type]            
        if index < 0 or index >= len(news_id_list_by_type):
            logging.info('index is not in the range of news_id_list_by_type {}'.format(news_id_list_by_type))
            return ''
        return news_id_list_by_type[index]                           

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