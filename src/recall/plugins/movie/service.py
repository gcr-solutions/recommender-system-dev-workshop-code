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
import time

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
    'AWS_REGION': 'ap-northeast-1',

    'UB_ITEM_VECTOR': 'ub_item_vector.index', 

    'RECALL_CONFIG': 'recall_config.pickle',

    'MOVIE_ID_MOVIE_PROPERTY': 'movie_id_movie_property_dict.pickle',
    'MOVIE_ID_MOVIE_CATEGORY': 'movie_category_movie_ids_dict.pickle',
    'MOVIE_ID_MOVIE_DIRECTOR': 'movie_director_movie_ids_dict.pickle',
    'MOVIE_ID_MOVIE_ACTOR': 'movie_actor_movie_ids_dict.pickle',
    'MOVIE_ID_MOVIE_LANGUAGE': 'movie_language_movie_ids_dict.pickle',
    'MOVIE_ID_MOVIE_LEVEL': 'movie_level_movie_ids_dict.pickle',
    'MOVIE_ID_MOVIE_YEAR': 'movie_year_movie_ids_dict.pickle',

    'UB_IDX_MAPPING': 'embed_raw_item_mapping.pickle',

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',

    'RECALL_PER_MOVIE_ID': 10, 
    'SIMILAR_ENTITY_THRESHOLD': 20, 
    'RECALL_THRESHOLD': 2.0, 
    'RECALL_MERGE_NUMBER': 20,

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,

    'PORTRAIT_SERVICE_ENDPOINT': 'http://portrait:5300',
    'PS_CONFIG': 'ps_config.json',
    'METHOD': "ps-complete",
    'PS_SIMS_BATCH_RESULT': 'ps-sims-batch.out'
}

# lastUpdate
localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
embedding_type = 'embedding'
pickle_type = 'inverted-list'
vector_index_type = 'vector-index'
json_type = 'ps-result'
out_type = 'ps-sims-dict'


class Recall(service_pb2_grpc.RecallServicer):

    serviceImpl: service_impl.ServiceImpl

    def __init__(self):
        logging.info('__init__(self)...')

        logging.debug('Initial self.serviceImpl...')
        self.serviceImpl = service_impl.ServiceImpl()       
        # Load index model for similarity searching
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        # logging.info('Files -> %s in %s', local_data_folder, os.listdir(local_data_folder))

        # # Ignored if files were not existed 
        # if os.path.isfile(ub_faiss_index_file) : 
        #     logging.info('Loading ub_faiss_index_file-> %s ...', ub_faiss_index_file)
        #     self.ub_faiss_index = faiss.read_index(ub_faiss_index_file)

        #     logging.debug('Initial self.serviceImpl...')
        #     self.serviceImpl = service_impl.ServiceImpl()

        index_file_list = [MANDATORY_ENV_VARS['UB_ITEM_VECTOR']]
        self.ub_faiss_index = None
        self.reload_vector_index(local_data_folder, index_file_list)
        # # Ignored if files were not existed 
        # if self.ub_faiss_index != None:

        # Load pickle files
        logging.info('Loading pickle file from NFS ...')
        # self.movie_id_word_ids_dict = self.load_pickle(movie_id_word_ids_file)
        # self.movie_id_entity_ids_dict = self.load_pickle(movie_id_entity_ids_file)
        # self.word_id_movie_ids_dict = self.load_pickle(word_id_movie_ids_file)
        # self.entity_id_movie_ids_dict = self.load_pickle(entity_id_movie_ids_file)
        # self.movie_id_keywords_dict = self.load_pickle(movie_id_keywords_file)
        # self.movie_id_movie_type_dict = self.load_pickle(movie_id_movie_type_file)
        # self.movie_type_movie_ids_dict = self.load_pickle(movie_type_movie_ids_file)
        # self.keyword_movie_ids_dict = self.load_pickle(keyword_movie_ids_file)

        # Load pickle files
        logging.info('Loading pickle file from NFS ...')
        pickle_file_list = [MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_PROPERTY'],MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_CATEGORY'],MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_DIRECTOR'],MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_ACTOR'],MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_LANGUAGE'],MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_LEVEL'],MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_YEAR'],MANDATORY_ENV_VARS['UB_IDX_MAPPING'],MANDATORY_ENV_VARS['RECALL_CONFIG']]
        self.reload_pickle_file(local_data_folder, pickle_file_list)

        out_file_list = [MANDATORY_ENV_VARS['PS_SIMS_BATCH_RESULT']]
        self.reload_out_file(local_data_folder, out_file_list)

    def reload_vector_index(self, file_path, file_list):
        logging.info('reload_vector_index file strat')
        for file_name in file_list:
            vector_index_file_path = file_path + file_name
            if MANDATORY_ENV_VARS['UB_ITEM_VECTOR'] in vector_index_file_path:
                if os.path.isfile(vector_index_file_path):
                    logging.info('reload_vector_index vector_index_file_path {}'.format(vector_index_file_path))
                    self.ub_faiss_index = faiss.read_index(vector_index_file_path)
                else:
                    logging.info('vector_index_file_path file is empty') 

    def reload_pickle_file(self, file_path, file_list):
        logging.info('reload_pickle_file  strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_PROPERTY'] in pickle_path:
                logging.info('reload movie_id_movie_property_dict file {}'.format(pickle_path))
                self.movie_id_movie_property_dict = self.load_pickle(pickle_path)
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_CATEGORY'] in pickle_path:
                logging.info('reload movie_id_movie_category_dict file {}'.format(pickle_path))
                self.movie_id_movie_category_dict = self.load_pickle(pickle_path)
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_DIRECTOR'] in pickle_path:
                logging.info('reload movie_id_movie_director_dict file {}'.format(pickle_path))
                self.movie_id_movie_director_dict = self.load_pickle(pickle_path)  
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_ACTOR'] in pickle_path:
                logging.info('reload movie_id_movie_actor_dict file {}'.format(pickle_path))
                self.movie_id_movie_actor_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_LANGUAGE'] in pickle_path:
                logging.info('reload movie_id_movie_language_dict file {}'.format(pickle_path))
                self.movie_id_movie_language_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_LEVEL'] in pickle_path:
                logging.info('reload movie_id_movie_level_dict file {}'.format(pickle_path))
                self.movie_id_movie_level_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_YEAR'] in pickle_path:
                logging.info('reload movie_id_movie_year_dict file {}'.format(pickle_path))
                self.movie_id_movie_year_dict = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['RECALL_CONFIG'] in pickle_path:
                logging.info('reload recall_config file {}'.format(pickle_path))
                self.recall_config = self.load_pickle(pickle_path) 
            if MANDATORY_ENV_VARS['UB_IDX_MAPPING'] in pickle_path:
                logging.info('reload ub_idx_mapping file {}'.format(pickle_path))
                self.ub_idx_mapping = self.load_pickle(pickle_path)                

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

    def reload_out_file(self, file_path, file_list):
        logging.info("reload_out_file start")
        for file_name in file_list:
            out_path = file_path + file_name
            logging.info("reload_out_type out_path {}".format(out_path))
            if MANDATORY_ENV_VARS['PS_SIMS_BATCH_RESULT'] in out_path:
                logging.info('reload ps_sims_batch_result file {}'.format(out_path))
                self.ps_sims_movie_ids_dict = self.load_out_file(out_path)

    def load_pickle(self, file):
        if os.path.isfile(file):
            infile = open(file, 'rb')
            dict = pickle.load(infile)
            infile.close()
            return dict
        else:
            logging.info('file {} is not existed'.format(file))
            return {}


    def load_out_file(self, file):
        logging.info("load_out_file start load {}".format(file))
        ps_sims_movie_ids_dict = {}
        if os.path.isfile(file):
            infile = open(file, 'rb')
            for line in infile.readlines():
                sims_recommend = json.loads(line)
                ps_sims_movie_ids_dict[sims_recommend['input']['itemId']] = sims_recommend['output']['recommendedItems']
            infile.close()
        else:
            logging.info('file {} is not existed'.format(file))
        return ps_sims_movie_ids_dict

    def Restart(self, request, context):
        logging.info('Restart(self, request, context)...')
        requestMessage = any_pb2.Any()
        request.dicts.Unpack(requestMessage)
        logging.info('Recieved notice for restart -> %s', requestMessage.value.decode('utf-8'))
        self.__init__()
        logging.info('Re-initial recall service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse

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
        if file_type == embedding_type:
            self.reload_embedding_files(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == pickle_type:
            self.reload_pickle_file(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == vector_index_type:
            self.reload_vector_index(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == out_type:
            self.reload_out_file(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)

        logging.info('Re-initial recall service.')
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

    def Status(self, request, context):
        logging.info('Status(self, request, context)...')
        status = any_pb2.Any()
        status.value =  json.dumps({
            "redis_status": rCache.connection_status(),
            "last_merge_result": localtime
        }).encode('utf-8')
        statusResponse = service_pb2.StatusResponse()
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
        reqData = json.loads(reqDicts.value, encoding='utf-8')
        user_id = reqData['user_id']
        clicked_movie_ids = reqData['clicked_item_ids']
        logging.info('user_id -> %s', user_id)
        logging.info('clicked_item_ids -> %s', clicked_movie_ids)
        
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
        user_portrait_result = httpResp.json()['results']
        logging.info('current user portrait: {}'.format(user_portrait_result))

        # 配置参数
        config_dict = {}
        recall_wrap = {}
        recall_wrap['content'] = self.movie_id_movie_property_dict
        recall_wrap['dict_wrap'] = {}
        recall_wrap['dict_wrap']['category'] = self.movie_id_movie_category_dict
        recall_wrap['dict_wrap']['director'] = self.movie_id_movie_director_dict
        recall_wrap['dict_wrap']['actor'] = self.movie_id_movie_actor_dict
        recall_wrap['dict_wrap']['language'] = self.movie_id_movie_language_dict
        recall_wrap['dict_wrap']['level'] = self.movie_id_movie_level_dict
        recall_wrap['dict_wrap']['year'] = self.movie_id_movie_year_dict
        recall_wrap['dict_wrap']['ps-sims'] = self.ps_sims_news_ids_dict
        recall_wrap['config'] = self.recall_config
        config_dict['recall_wrap'] = recall_wrap
        config_dict['method'] = MANDATORY_ENV_VARS['METHOD']
        recall_wrap['ub_index'] = self.ub_faiss_index
        recall_wrap['ub_idx_mapping'] = self.ub_idx_mapping

        config_dict['user_portrait'] = user_portrait_result

        recall_result = self.serviceImpl.merge_recall_result([str(elem) for elem in clicked_movie_ids],
                                                                                        **config_dict)

        # recall_result = self.serviceImpl.merge_recall_result(clicked_movie_ids, 
        #                     self.movie_id_word_ids_dict, 
        #                     self.movie_id_entity_ids_dict, 
        #                     self.word_id_movie_ids_dict, 
        #                     self.entity_id_movie_ids_dict,
        #                     self.movie_id_keywords_dict,
        #                     self.movie_id_movie_type_dict,
        #                     self.movie_type_movie_ids_dict,
        #                     user_portrait,
        #                     self.keyword_movie_ids_dict)
      
        mergeResponseAny = any_pb2.Any()
        mergeResponseAny.value =  json.dumps(recall_result).encode('utf-8')
        mergeResponse = service_pb2.MergeResultResponse(code=0, description='merged with success')
        mergeResponse.results.Pack(mergeResponseAny)
        return mergeResponse

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
    logging.info('recall plugin init end!')


def serve(plugin_name):
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
    init()
    serve(os.environ.get("PLUGIN_NAME", "default"))