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

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,

    'NEWS_TYPE_NEWS_IDS': 'news_type_news_ids_dict.pickle',
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

        self.reload_pickle_type(local_data_folder, file_list)

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

        if file_type == pickle_type:
            self.reload_pickle_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        logging.info('Re-initial filter service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse 

    def reload_pickle_type(self, file_path, file_list):
        logging.info('reload_pickle_type  strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))                 
            if MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload news_type_news_ids_dict file {}'.format(pickle_path))
                    self.news_type_news_ids_dict = self.load_pickle(pickle_path) 
                else:
                    logging.info('reload news_type_news_ids_dict, file is empty')         

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

        logging.info("rank result {}".format(rank_result))

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
                logging.info('recommend news list to user')
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
            logging.info('get news list by news type {}'.format(recommend_type))
            if recommend_type not in lCfgCompleteType:
                return recommend_list           
            logging.info('Get news_type_news_ids_dict completed')
            if not bool(self.news_type_news_ids_dict):
                recommend_list
            news_id_list = self.news_type_news_ids_dict[recommend_type]
            recommend_list = self.generate_news_list_by_type(news_id_list)

        return recommend_list

    def generate_cold_start_data(self, user_id):
        logging.info('start cold start algorithm')           
        coldstart_news_list = []
        new_filter_record = []
        i = 0
        while len(coldstart_news_list) < int(MANDATORY_ENV_VARS['COLDSTART_NEWS_COUNT']):
            index = i % len(lCfgCompleteType)
            temp_news_id = self.sample_by_type(lCfgCompleteType[index])
            if temp_news_id == None:
                logging.info('Cannot get news id')
                return []
            logging.info('get sample news id {} by type {}'.format(temp_news_id, lCfgCompleteType[index]))
            if temp_news_id not in coldstart_news_list:
                coldstart_news_list.append({
                    temp_news_id : tColdstart
                })
            i = i + 1
        new_filter_record.append({
            calendar.timegm(time.gmtime()): coldstart_news_list
        })

        logging.info('coldstart filter record {}'.format(new_filter_record))
            
        if rCache.load_data_into_hash(user_id_filter_dict, user_id, json.dumps(new_filter_record).encode('utf-8')):
            logging.info('Save filter data into Redis with key : %s ', user_id) 
        return new_filter_record                   


    def generate_news_list_by_type(self, news_id_list):
        news_recommend_list = []
        count = 0
        present_recommend_news_id_list = []
        while count < int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']):
            news, news_id = self.get_random_news(news_id_list)
            if news_id not in present_recommend_news_id_list:
                news_recommend_list.append(news)
                present_recommend_news_id_list.append(news_id)
                count = count + 1

        return news_recommend_list 

    def get_random_news(self, news_id_list):
        logging.info('get_random_news_id start')
        index = random.randint(0,len(news_id_list) -1)
        return {
            'id': news_id_list[index],
            'tag': ''
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
            new_recommend_list, present_recommend_news_id_list, remain_count = self.get_present_recommend_news_list(user_id, filtered_data, recommended_news_list, int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']))
        else:
            hot_topic_count = hot_topic_count_array[random.randint(0,len(hot_topic_count_array) -1)]
            new_recommend_list, present_recommend_news_id_list, remain_count = self.get_present_recommend_news_list(user_id, filtered_data, recommended_news_list, int(MANDATORY_ENV_VARS['RECOMMEND_ITEM_COUNT']) - hot_topic_count)
            logging.info('need hot topic news')
            hot_topic_news_list = self.get_hot_topic_news_list(user_id, hot_topic_count)
            new_recommend_list = hot_topic_news_list + new_recommend_list

        logging.info('present_recommend_record_list {}'.format(present_recommend_news_id_list))
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
        logging.info('recommended_data {} for user {}'.format(recommended_data, user_id))    
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
        for k,v in filtered_data[0].items():
            logging.info('filtered_data first element {}'.format(v))
            for k1, v1 in v[0].items():
                logging.info('filtered_data first news recommend type {}'.format(v1))
                if v1 == tColdstart:
                    return True
        return False  

    def get_present_recommend_news_list(self, user_id, filtered_data, recommended_news_list, news_list_count):
        news_recommend_list = [] #[{'id':'news_id1', 'tag': 'recommend'},{'id':'news_id2', 'tag': 'recommend'}]
        present_recommend_news_id_list = [] #['news_id1','news_id2']
        recommend_count = 0
        remain_count = 0
        for element in filtered_data:
            for k, v in element.items():
                for news_data in v: 
                    for k1, v1 in news_data.items():
                        if k1 not in recommended_news_list and k1 not in present_recommend_news_id_list:
                            if recommend_count < news_list_count:
                                news_recommend_list.append({
                                    'id': k1,
                                    'tag': v1
                                }) 
                                present_recommend_news_id_list.append(k1)
                                recommend_count = recommend_count + 1
                            else:
                                # record the length of remain news list
                                remain_count = remain_count + 1
        news_lacking_count = news_list_count - len(present_recommend_news_id_list)
        if news_lacking_count > 0:
            logging.info('complement news list, count {}'.format(str(news_lacking_count)))
            complement_news_recommend_list = []
            complement_present_recommend_news_id_list = []

            complement_news_recommend_list, complement_present_recommend_news_id_list = self.get_complement_news_recommend_list(user_id, present_recommend_news_id_list, news_lacking_count)
            news_recommend_list = news_recommend_list + complement_news_recommend_list
            present_recommend_news_id_list = present_recommend_news_id_list + complement_present_recommend_news_id_list
        return news_recommend_list, present_recommend_news_id_list, remain_count                                                           

    def get_complement_news_recommend_list(self, user_id, present_recommend_news_id_list, news_lacking_count):
        logging.info('complement_news_recommend_list start')
        complement_news_recommend_list = []
        complement_present_recommend_news_id_list = []
        count = 0

        sort_type = []
        httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
        if httpResp.status_code != 200:
            return complement_news_recommend_list, complement_present_recommend_news_id_list
        user_portrait = httpResp.json()          
         
        logging.info('user_portrait: {}'.format(user_portrait))
        user_portrait_result = user_portrait['results']
        dict_type = {}
        for item_type, kwsc in user_portrait_result.items():
            sort_type.append((item_type, kwsc['avg']))
            dict_type[item_type] = kwsc['avg']
        sort_type.sort(key = lambda x: x[1], reverse = True)
        logging.info('sort_type {}'.format(sort_type))

        while count < news_lacking_count:
            sort_type_count = 0
            while sort_type_count < len(sort_type) and count < news_lacking_count:
                news_id = self.sample_by_type(sort_type[sort_type_count][0])
                if (news_id not in present_recommend_news_id_list and news_id not in complement_present_recommend_news_id_list and news_id != ''):
                    logging.info("get hot topic news id {}".format(news_id))
                    complement_news_recommend_list.append({
                        'id': news_id,
                        'tag': tRecommend
                    })
                    complement_present_recommend_news_id_list.append(news_id)
                    count = count + 1
                    sort_type_count = sort_type_count + 1
            if count < news_lacking_count:    
                diversity_news_id = self.get_diversity_news_id(present_recommend_news_id_list, complement_present_recommend_news_id_list)
                complement_news_recommend_list.append({
                    'id': diversity_news_id,
                    'tag': tDiversity
                })
                complement_present_recommend_news_id_list.append(diversity_news_id)
                count = count + 1
        return complement_news_recommend_list, complement_present_recommend_news_id_list        

    def get_diversity_news_id(self, present_recommend_news_id_list, complement_present_recommend_news_id_list):
        logging.info('get_diversity_news_id start')
        while True:
            news_type = lCfgCompleteType[random.randint(0,len(lCfgCompleteType) -1)]
            news_id = self.sample_by_type(news_type)
            if (news_id not in present_recommend_news_id_list and news_id not in complement_present_recommend_news_id_list and news_id != ''):
                return news_id        

    def get_hot_topic_news_list(self, user_id, hot_topic_count):
        news_list = []
        hot_topic_type = self.get_hot_topic_type(user_id)
        if hot_topic_type == '':
            return []
        count = 0
        while count < hot_topic_count:
            news_id = self.sample_by_type(hot_topic_type[0])
            if news_id == '':
                return []
            logging.info("get hot topic news id {}".format(news_id))
            news_list.append({
                'id': news_id,
                'tag': tRecommend
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
        dict_type = {}
        for item_type, kwsc in user_portrait_result.items():
            sort_type.append((item_type, kwsc['avg']))
            dict_type[item_type] = kwsc['avg']
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
                for k1, v1 in v[0].items():
                    logging.info('existed_filter_record first news recommend type {}'.format(v1))
                    if v1 == tColdstart:
                        logging.info('there is coldstart data, clear them')
                        existed_filter_record = []

        new_filter_record = self.generate_new_filter_record(existed_filter_record, recall_result, rank_result, user_portrait_result)
        logging.info('new_filter_record {}'.format(new_filter_record))

        existed_filter_record.insert(0, {calendar.timegm(time.gmtime()): new_filter_record})

        if rCache.load_data_into_hash(user_id_filter_dict, user_id, json.dumps(existed_filter_record).encode('utf-8')):
            logging.info('Save filter data into Redis with key : %s ', user_id)
        logging.info('final existed_filter_record {}'.format(existed_filter_record))
        logging.info('filter_process completed')

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
    def generate_new_filter_record(self, current_filter_record, recall_result, rank_result, user_portrait):
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