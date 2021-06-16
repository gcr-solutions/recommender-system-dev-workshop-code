from concurrent import futures
import logging
import os
import json
from datetime import datetime
import pickle
import sys

from google.protobuf import any_pb2
import grpc
from grpc_reflection.v1alpha import reflection

import cache

import service_pb2
import service_pb2_grpc

# Environments for service
MANDATORY_ENV_VARS = {
    'NEWS_ID_KEYWORDS_TFIDF': 'news_id_keywords_tfidf_dict.pickle',
    'NEWS_ID_KEYWORDS': 'news_id_keywords_dict.pickle',
    'NEWS_ID_NEWS_TYPE': 'news_id_news_type_dict.pickle',

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
        pickle_file_list = [MANDATORY_ENV_VARS['NEWS_ID_KEYWORDS_TFIDF'],MANDATORY_ENV_VARS['NEWS_ID_KEYWORDS'],MANDATORY_ENV_VARS['NEWS_ID_NEWS_TYPE']]
        self.reload_pickle_file(local_data_folder, pickle_file_list)

    def reload_pickle_file(self, file_path, file_list):
        logging.info('reload_pickle_file  strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['NEWS_ID_KEYWORDS_TFIDF'] in pickle_path:
                logging.info('reload news_id_keywords_tfidf_dict file {}'.format(pickle_path))
                self.news_id_keywords_tfidf_dict = self.load_pickle(pickle_path)
            if MANDATORY_ENV_VARS['NEWS_ID_KEYWORDS'] in pickle_path:
                logging.info('reload news_id_keywords_dict file {}'.format(pickle_path))
                self.news_id_keywords_dict = self.load_pickle(pickle_path)
                logging.info('news_id_keywords_dict {}'.format(self.news_id_keywords_dict)) 
            if MANDATORY_ENV_VARS['NEWS_ID_NEWS_TYPE'] in pickle_path:
                logging.info('reload news_id_news_type_dict file {}'.format(pickle_path))
                self.news_id_news_type_dict = self.load_pickle(pickle_path)                     

    def load_pickle(self, file):
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = pickle.load(infile)
            infile.close()
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
        get_user_portrait_result = rCache.get_user_portrait(user_id)
        # User profile decay
        decay_ratio = 0.8
        value_per_update = 5
        current_click_mark = 0
        if get_user_portrait_result != None and bool(get_user_portrait_result):
            user_portrait = json.loads(get_user_portrait_result.decode('utf-8'))
            # get current click mark
            for k, v in user_portrait.items():
                if user_portrait[k]['mark'] > current_click_mark:
                    current_click_mark = user_portrait[k]['mark']
            for k, v in user_portrait.items():
                if user_portrait[k]['mark'] != current_click_mark:
                    user_portrait[k]['avg'] = user_portrait[k]['avg'] * decay_ratio
                    # for kw, sc in v.items():
                    #     user_portrait[k][kw] = sc * decay_ratio
        logging.info("get original user portrait is {}".format(user_portrait))

        # Read data from Redis
        keywords_list = self.get_keywords(clicked_news_ids)
        logging.info('keywords_list -> %s', keywords_list)
        for news_id in clicked_news_ids:
            # update type 
            current_type = self.news_id_news_type_dict[news_id]
            logging.info('current type -> %s', current_type)
            if current_type not in user_portrait:
                user_portrait[current_type] = {}
                user_portrait[current_type]['avg'] = 1.0
                user_portrait[current_type]['mark'] = current_click_mark + 1
            else:
                user_portrait[current_type]['avg'] = user_portrait[current_type]['avg'] * (decay_ratio + 0.4)
                user_portrait[current_type]['mark'] = current_click_mark + 1
            news_id_keywords_tfidf_dict = self.get_news_id_keywords_tfidf_dict(news_id)
            # analyze keywords
            if keywords_list:
                for keywords in keywords_list:
                    logging.info('keywords -> %s', keywords)
                    for k in keywords.split(','):
                        logging.info('k -> %s', k)
                        if news_id_keywords_tfidf_dict is not None:
                            if k not in user_portrait[current_type]:
                                user_portrait[current_type][k] = news_id_keywords_tfidf_dict[k]
                            else:
                                current_score = user_portrait[current_type][k]
                                user_portrait[current_type][k] = current_score + news_id_keywords_tfidf_dict[k]

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