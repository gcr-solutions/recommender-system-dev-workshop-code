from concurrent import futures
import logging
import os
import json
import uuid
from datetime import datetime
import faiss
import pickle
import numpy as np
import requests
import sys

from google.protobuf import descriptor
from google.protobuf import any_pb2
import grpc
from grpc_reflection.v1alpha import reflection

import service_impl
import cache

import service_pb2
import service_pb2_grpc

# Environments for service
MANDATORY_ENV_VARS = {

    'NEWS_ID_KEYWORDS_TFIDF': 'news_id_keywords_tfidf_dict.pickle',
    'ENTITY_ID_NEWS_IDS': 'entity_id_news_ids_dict.pickle',
    'NEWS_ID_ENTITY_IDS': 'news_id_entity_ids_dict.pickle',
    'NEWS_ID_KEYWORDS': 'news_id_keywords_dict.pickle',
    'NEWS_ID_NEWS_TITLE': 'news_id_news_title_dict.pickle',
    'NEWS_ID_NEWS_TYPE': 'news_id_news_type_dict.pickle',
    'NEWS_ID_WORD_IDS': 'news_id_word_ids_dict.pickle',
    'KEYWORD_NEWS_IDS': 'keyword_news_ids_dict.pickle',
    'NEWS_TYPE_NEWS_IDS': 'news_type_news_ids_dict.pickle',
    'WORD_ID_NEWS_IDS': 'word_id_news_ids_dict.pickle',

    'ENTITY_INDEX': 'recommender-system-news-toutiao-entity-vector.index', 
    'WORD_INDEX': 'recommender-system-news-toutiao-word-vector.index', 
    'ENTITY_EMBEDDING_NPY': 'dkn_entity_embedding.npy',

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',

    'RECALL_PER_NEWS_ID': 10, 
    'SIMILAR_ENTITY_THRESHOLD': 20, 
    'RECALL_THRESHOLD': 2.0, 
    'RECALL_MERGE_NUMBER': 20,

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,

    'PORTRAIT_SERVICE_ENDPOINT': 'http://portrait:5300'
}

embedding_type = 'embedding'
pickle_type = 'inverted-list'
vector_index_type = 'vector-index'

# lastUpdate
localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

class Recall(service_pb2_grpc.RecallServicer):

    serviceImpl: service_impl.ServiceImpl
    def __init__(self):
        logging.info('__init__(self)...')
        # Load index model for similarity searching
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        # logging.info('Files -> %s in %s', local_data_folder, os.listdir(local_data_folder))

        index_file_list = [MANDATORY_ENV_VARS['ENTITY_INDEX'],MANDATORY_ENV_VARS['WORD_INDEX']]
        self.entity_index = None
        self.word_index = None
        self.entity_embedding = np.array([])

        self.reload_vector_index(local_data_folder, index_file_list)

        self.reload_embedding_files(local_data_folder, [MANDATORY_ENV_VARS['ENTITY_EMBEDDING_NPY']])

        # Ignored if files were not existed 
        if self.entity_index != None and self.word_index != None and self.entity_embedding.size != 0:

            logging.debug('Initial self.serviceImpl...')
            self.serviceImpl = service_impl.ServiceImpl(recall_per_news_id=MANDATORY_ENV_VARS['RECALL_PER_NEWS_ID'], 
                        similar_entity_threshold=MANDATORY_ENV_VARS['SIMILAR_ENTITY_THRESHOLD'], 
                        recall_threshold=MANDATORY_ENV_VARS['RECALL_THRESHOLD'], 
                        recall_merge_number=MANDATORY_ENV_VARS['RECALL_MERGE_NUMBER'],
                        entity_index_l=self.entity_index,
                        word_index_l=self.word_index, 
                        entity_embedding_l=self.entity_embedding)

        # Load pickle files
        logging.info('Loading pickle file from NFS ...')
        pickle_file_list = [MANDATORY_ENV_VARS['NEWS_ID_WORD_IDS'],MANDATORY_ENV_VARS['NEWS_ID_ENTITY_IDS'],MANDATORY_ENV_VARS['NEWS_ID_ENTITY_IDS'],MANDATORY_ENV_VARS['ENTITY_ID_NEWS_IDS'],MANDATORY_ENV_VARS['NEWS_ID_KEYWORDS'],MANDATORY_ENV_VARS['NEWS_ID_NEWS_TYPE'],MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'],MANDATORY_ENV_VARS['KEYWORD_NEWS_IDS']]
        self.reload_pickle_file(local_data_folder, pickle_file_list)

    def reload_vector_index(self, file_path, file_list):
        logging.info('reload_vector_index file strat')
        for file_name in file_list:
            vector_index_file_path = file_path + file_name
            if 'entity' in vector_index_file_path:
                if os.path.isfile(vector_index_file_path):
                    logging.info('reload_vector_index vector_index_file_path {}'.format(vector_index_file_path))
                    self.entity_index = faiss.read_index(vector_index_file_path)
                else:
                    logging.info('vector_index_file_path file is empty') 
            if 'word' in vector_index_file_path:
                if os.path.isfile(vector_index_file_path):
                    logging.info('reload_vector_index vector_index_file_path {}'.format(vector_index_file_path))
                    self.word_index = faiss.read_index(vector_index_file_path)
                else:
                    logging.info('vector_index_file_path file is empty')

    def reload_pickle_file(self, file_path, file_list):
        logging.info('reload_pickle_file  strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['NEWS_ID_WORD_IDS'] in pickle_path:
                logging.info('reload news_id_word_ids_dict file {}'.format(pickle_path))
                self.news_id_word_ids_dict = self.load_pickle(pickle_path)
            if MANDATORY_ENV_VARS['NEWS_ID_ENTITY_IDS'] in pickle_path:
                logging.info('reload news_id_entity_ids_dict file {}'.format(pickle_path))
                self.news_id_entity_ids_dict = self.load_pickle(pickle_path)
            if MANDATORY_ENV_VARS['NEWS_ID_ENTITY_IDS'] in pickle_path:
                logging.info('reload word_id_news_ids_dict file {}'.format(pickle_path))
                self.word_id_news_ids_dict = self.load_pickle(pickle_path)  
            if MANDATORY_ENV_VARS['ENTITY_ID_NEWS_IDS'] in pickle_path:
                logging.info('reload entity_id_news_ids_dict file {}'.format(pickle_path))
                self.entity_id_news_ids_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['NEWS_ID_KEYWORDS'] in pickle_path:
                logging.info('reload news_id_keywords_dict file {}'.format(pickle_path))
                self.news_id_keywords_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['NEWS_ID_NEWS_TYPE'] in pickle_path:
                logging.info('reload news_id_news_type_dict file {}'.format(pickle_path))
                self.news_id_news_type_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['NEWS_TYPE_NEWS_IDS'] in pickle_path:
                logging.info('reload news_type_news_ids_dict file {}'.format(pickle_path))
                self.news_type_news_ids_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['KEYWORD_NEWS_IDS'] in pickle_path:
                logging.info('reload keyword_news_ids_dict file {}'.format(pickle_path))
                self.keyword_news_ids_dict = self.load_pickle(pickle_path)                                                                                          

    def reload_embedding_files(self, file_path, file_list):
        logging.info('reload_embedding_files  strat')
        for file_name in file_list:
            embedding_path = file_path + file_name
            logging.info('reload_embedding_files embedding_path {}'.format(embedding_path))
            if 'entity' in embedding_path:
                if os.path.isfile(embedding_path):
                    logging.info('reload entity_embed')
                    self.entity_embedding = np.load(embedding_path)
                else:
                    logging.info('entity_embed is empty') 

    def load_pickle(self, file):
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = pickle.load(infile)
            infile.close()
            return dict
        else:
            logging.info('file {} is not existed'.format(file))
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


        if file_type == embedding_type:
            self.reload_embedding_files(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == pickle_type:
            self.reload_pickle_file(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == vector_index_type:
            self.reload_vector_index(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)

        logging.info('Re-initial recall service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse

    def Status(self, request, context):
        logging.info('Status(self, request, context)...')
        status = any_pb2.Any()
        status.value =  json.dumps({
            "redis_status": rCache.connection_status(),
            "last_merge_result": localtime
        }).encode('utf-8')
        statusResponse = service_pb2.StatusResponse(code=0)
        statusResponse.status.Pack(status)
        return statusResponse

    def Stop(self, request, context):
        logging.info('Stop(self, request, context)...')
        logging.info('Recieved singal -> %d', request.signal)
        commonResponse = service_pb2.CommonResponse(code=0, description='stop with doing nothing')
        return commonResponse

    def MergeResult(self, request, context):
        logging.info('MergeResult(self, request, context)...')
        logging.info('Start recall->process()...')
        # Generate recall id & time
        recall_id = uuid.uuid4().__str__()
        localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        logging.info('Generated recall_id -> %s at %s', recall_id, localtime)
        # Retrieve request data        
        reqDicts = any_pb2.Any()
        request.dicts.Unpack(reqDicts)

        logging.info('Recieved recall process request -> {}'.format(reqDicts))
        reqDictsJson = json.loads(reqDicts.value, encoding='utf-8')
        user_id = reqDictsJson['user_id']
        clicked_item_ids = reqDictsJson['clicked_item_ids']
        logging.info('user_id -> %s', user_id)
        logging.info('clicked_item_ids -> %s', clicked_item_ids)
        
        # Prevent failure due to ignore intial at very begining
        try:
            self.serviceImpl
        except NameError:
            logging.info('re-initial recall service...')
            self.__init__()

        # Get user portrait from portrait service
        httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
        if httpResp.status_code != 200:
            return service_pb2.MergeResultResponse(code=-1, description=('Failed to get portrait for -> {}').format(user_id))
        user_portrait = httpResp.json()

        user_portrait_result = user_portrait['results']
        logging.info('current user portrait: {}'.format(user_portrait_result))

        recall_result = self.serviceImpl.merge_recall_result(clicked_item_ids, 
                            self.news_id_word_ids_dict, 
                            self.news_id_entity_ids_dict, 
                            self.word_id_news_ids_dict, 
                            self.entity_id_news_ids_dict,
                            self.news_id_keywords_dict,
                            self.news_id_news_type_dict,
                            self.news_type_news_ids_dict,
                            user_portrait_result,
                            self.keyword_news_ids_dict)

        logging.info('generate recall result: {}'.format(recall_result))

        mergeResponseAny = any_pb2.Any()
        mergeResponseAny.value =  json.dumps(recall_result).encode('utf-8')
        mergeResponse = service_pb2.MergeResultResponse(code=0, description='merged with success')
        mergeResponse.results.Pack(mergeResponseAny)
        return mergeResponse



def init():
    # Check out environments
    logging.info('recall init start!')
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var]=os.environ.get(var)
    
    # Initial redis connection
    global rCache
    rCache = cache.RedisCache(host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])
    logging.info('recall init end!')



def serve(plugin_name):
    logging.info('recall serve end!')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    service_pb2_grpc.add_RecallServicer_to_server(Recall(), server)
    SERVICE_NAMES = (
        service_pb2.DESCRIPTOR.services_by_name['Recall'].full_name,
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
    logging.info('recall plugin start!')
    init()
    serve(os.environ.get("PLUGIN_NAME", "default"))