from concurrent import futures
import logging
import os
import json
from datetime import datetime
import pickle
import sys
import numpy as np
import time

from google.protobuf import any_pb2
import grpc
from grpc_reflection.v1alpha import reflection

import cache

import service_pb2
import service_pb2_grpc

# Environments for service
MANDATORY_ENV_VARS = {
    'NEWS_ID_PROPERTY': 'news_id_news_property_dict.pickle',
    'ENTITY_ID_NEWS_IDS': 'news_entities_news_ids_dict.pickle',
    'KEYWORD_NEWS_IDS': 'news_keywords_news_ids_dict.pickle',
    'NEWS_TYPE_NEWS_IDS': 'news_type_news_ids_dict.pickle',
    'WORD_ID_NEWS_IDS': 'news_words_news_ids_dict.pickle',
    'PORTRAIT_BATCH': 'portrait.pickle',

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
}

pickle_type = 'inverted-list'

# lastUpdate
getLastCall = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
updateLastCall = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

class Portrait(service_pb2_grpc.PortraitServicer):

    def __init__(self):
        logging.info('__init__(self)...')

        # Load index model for similarity searching
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        # logging.info('Files -> %s in %s', local_data_folder, os.listdir(local_data_folder))
        pickle_file_list = []
        pickle_file_list.append(MANDATORY_ENV_VARS['ENTITY_ID_NEWS_IDS'])
        pickle_file_list.append(MANDATORY_ENV_VARS['KEYWORD_NEWS_IDS'])
        pickle_file_list.append(MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'])
        pickle_file_list.append(MANDATORY_ENV_VARS['WORD_ID_NEWS_IDS'])
        pickle_file_list.append(MANDATORY_ENV_VARS['NEWS_ID_PROPERTY'])
        pickle_file_list.append(MANDATORY_ENV_VARS['PORTRAIT_BATCH'])
        self.reload_pickle_file(local_data_folder, pickle_file_list)

    def reload_pickle_file(self, file_path, file_list):
        logging.info('reload_pickle_file  strat')       
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['NEWS_ID_PROPERTY'] in pickle_path:
                logging.info('reload news_id_news_property_dict file {}'.format(pickle_path))
                self.news_id_news_property_dict = self.load_pickle(pickle_path)
            if MANDATORY_ENV_VARS['ENTITY_ID_NEWS_IDS'] in pickle_path:
                logging.info('reload entity_id_news_ids_dict file {}'.format(pickle_path))
                self.entity_id_news_ids_dict = self.load_pickle(pickle_path)  
            if MANDATORY_ENV_VARS['WORD_ID_NEWS_IDS'] in pickle_path:
                logging.info('reload word_id_news_ids_dict file {}'.format(pickle_path))
                self.word_id_news_ids_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'] in pickle_path:
                logging.info('reload news_type_news_ids_dict file {}'.format(pickle_path))
                self.news_type_news_ids_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['KEYWORD_NEWS_IDS'] in pickle_path:
                logging.info('reload keyword_news_ids_dict file {}'.format(pickle_path))
                self.keywords_news_ids_dict = self.load_pickle(pickle_path)                                                                                          
            if MANDATORY_ENV_VARS['PORTRAIT_BATCH'] in pickle_path:
                logging.info('batch reload portrait file {}'.format(pickle_path))
                self.batch_reload_pickle_files(pickle_path)
                # self.raw_embed_user_mapping_dict = self.load_pickle(pickle_path)                     
                logging.info('successful batch reload portrait file')

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

    def batch_reload_pickle_files(self, file):
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return json.JSONEncoder.default(self, obj)
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = pickle.load(infile)
            infile.close()
            # update to redis
            for k, v in dict.items():
                # Save into Redis
                rCache.save_user_portrait(k, json.dumps(v, cls=NumpyEncoder).encode('utf-8'))

            return dict
        else:
            return {}

    def Reload(self, request, context):
        logging.info('Reload(self, request, context)...')
        requestMessage = any_pb2.Any()
        request.dicts.Unpack(requestMessage)

        logging.info('Recieved notice requestMessage -> {}'.format(requestMessage))
        requestMessageJson = json.loads(requestMessage.value, encoding='utf-8')
        file_type = requestMessageJson['file_type']
        file_list = eval(requestMessageJson['file_list'])
        logging.info('file_type -> {}'.format(file_type))
        logging.info('file_list -> {}'.format(file_list)) 
        self.check_files_ready(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list, 0) 
        if file_type == pickle_type:
            self.reload_pickle_file(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        logging.info('Re-initial filter service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse 

    def Status(self, request, context):
        logging.info('Status(self, request, context)...')
        status = any_pb2.Any()
        status.value =  json.dumps({
            "redis_status": rCache.connection_status(),
            "last_get_portrait": getLastCall,
            "last_update_portrait": updateLastCall
        }).encode('utf-8')
        statusResponse = service_pb2.StatusResponse(code=0)
        statusResponse.status.Pack(status)
        return statusResponse

    def Stop(self, request, context):
        logging.info('Stop(self, request, context)...')
        logging.info('Recieved singal -> %d', request.signal)
        commonResponse = service_pb2.CommonResponse(code=0, description='stop with doing nothing')
        return commonResponse

    def GetPortrait(self, request, context):
        logging.info('GetPortrait(self, request, context)...')
        user_id = request.userId
        logging.info('user_id -> %s', user_id)
        # Read cached data from Redis & return 
        user_portrait_data = rCache.get_user_portrait(user_id)
        user_portrait = {}
        if  user_portrait_data != None and not bool(user_portrait):
            user_portrait = json.loads(user_portrait_data.decode('utf-8'))
        
        portraitResponseAny = any_pb2.Any()
        portraitResponseAny.value =  json.dumps(user_portrait).encode('utf-8')
        portraitResponse = service_pb2.PortraitResponse(code=0, description='Got portrait with success')
        portraitResponse.results.Pack(portraitResponseAny)
        return portraitResponse

    def update_portrait_under_a_property(self, mt_content, mt_up, ratio):
        # decay logic
        for k, v in mt_up.items():
            if k != 'recent':
                if mt_up[k]['mark'] != '1':
                    mt_up[k]['score'] = mt_up[k]['score'] * ratio
                else:
                    mt_up[k]['mark'] = '0'

        # update logic
        for ct in mt_content:
            if ct != None:
                if ct not in mt_up:
                    mt_up[ct] = {}
                    mt_up[ct]['mark'] = '1'
                    mt_up[ct]['score'] = 1.0
                else:
                    mt_up[ct]['mark'] = '1'
                    mt_up[ct]['score'] = mt_up[ct]['score'] + 1.0

        # find large score
        for k, v in mt_up.items():
            # update large score and type
            if k != 'recent':
                if mt_up[k]['score'] >= mt_up['recent'][1] and k not in mt_up['recent'][0]:
                    mt_up['recent'][0].append(k)
                    mt_up['recent'][1] = mt_up[k]['score']

    ########################################
    # 用户画像更新逻辑
    # 数据结构:
    # 'language':{'xx':{'mark':,'score':},...{'recent':['xx',score]}}
    # 'embedding':{'review':xxx,'photo':xxx,'ub':xxx}
    ########################################
    def update_user_portrait_with_one_click(self, current_user_portrait, current_read_item):
        #     # load user portrait for testing
        #     file_to_load = open("info/user_portrait_{}.pickle".format(user_name), "rb")
        #     current_user_portrait = pickle.load(file_to_load)
        #     print("load user portrait of the content is {}".format(current_user_portrait))

        # 用户兴趣衰减系数
        decay_ratio = 0.8

        popularity_method_list = ['keywords','type']

        for mt in popularity_method_list:
            self.update_portrait_under_a_property(
                self.news_id_news_property_dict[current_read_item][mt], current_user_portrait[mt], decay_ratio)

    def get_keywords(self, news_ids):
        keywords = []
        for news_id in news_ids:
            keywords.append(self.news_id_keywords_dict[news_id])
            # keywords = keywords + self.news_id_keywords_dict()[news_id]
        return keywords

    def get_news_id_keywords_tfidf_dict(self, news_id):
            return self.news_id_keywords_tfidf_dict[news_id]

    def UpdatePortrait(self, request, context):
        logging.info('UpdatePortrait(self, request, context)...')
        user_portrait = {}
    
        # Update portrait & save latest data into Redis & return latest data
        # Read data from request
        reqDicts = any_pb2.Any()
        request.dicts.Unpack(reqDicts)

        logging.info('Recieved requestMessage -> {}'.format(reqDicts))
        reqDictsJson = json.loads(reqDicts.value, encoding='utf-8')
        user_id = reqDictsJson['user_id']
        clicked_news_ids = reqDictsJson['clicked_item_ids']
        logging.info('user_id -> %s', user_id)
        logging.info('clicked_news_ids -> %s', clicked_news_ids)       

        # Get original portrait
        user_portrait_data = rCache.get_user_portrait(user_id)
        user_portrait = {}
        if  user_portrait_data != None and not bool(user_portrait):
            user_portrait = json.loads(user_portrait_data.decode('utf-8'))
        else:
            #initial user portrait
            popularity_method_list = ['keywords', 'type']
            for mt in popularity_method_list:
                user_portrait[mt] = {}
                user_portrait[mt]['recent'] = []
                user_portrait[mt]['recent'].append([])
                user_portrait[mt]['recent'].append(0.0)
        dict_user_portrait = {}
        dict_user_portrait[str(user_id)] = user_portrait 

        print("update user portrait for users")
        user_click_records = {}
        user_click_records[user_id] = clicked_news_ids
        for user_id, input_item_list in user_click_records.items():
            print("user id {} item list {}".format(user_id, input_item_list))
            for ci in input_item_list:
                self.update_user_portrait_with_one_click(dict_user_portrait[str(user_id)], str(ci))
            
        user_portrait = dict_user_portrait[str(user_id)]
        # Save into Redis
        logging.info('user_portrait -> %s', user_portrait)
        if bool(user_portrait):
            logging.info('Save user_portrait into Redis.')
            rCache.save_user_portrait(user_id, json.dumps(user_portrait).encode('utf-8'))
            logging.info('Saving has done.')

        ###
        logging.info('update_portrait() has done.')
        portraitResponseAny = any_pb2.Any()
        portraitResponseAny.value =  json.dumps(user_portrait).encode('utf-8')
        portraitResponse = service_pb2.PortraitResponse(code=0, description='Update portrait with success')
        portraitResponse.results.Pack(portraitResponseAny)
        return portraitResponse

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
    service_pb2_grpc.add_PortraitServicer_to_server(Portrait(), server)
    SERVICE_NAMES = (
        service_pb2.DESCRIPTOR.services_by_name['Portrait'].full_name,
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
    init()
    serve(os.environ.get("PLUGIN_NAME", "default"))