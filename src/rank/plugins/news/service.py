from concurrent import futures
import logging
import os
import json
import uuid
from datetime import datetime
import pickle
import numpy as np
import requests
import sys
import time

import tarfile
import glob
from tensorflow.contrib import predictor

from google.protobuf import descriptor
from google.protobuf import any_pb2
import grpc
from grpc_reflection.v1alpha import reflection
from google.protobuf.any_pb2 import Any

import service_pb2
import service_pb2_grpc

# Environments for service
MANDATORY_ENV_VARS = {

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',
    'NEWS_ID_FEATURE': 'news_id_news_feature_dict.pickle',
    'MODEL_EXTRACT_DIR': '/opt/ml/model/',
    'DEMO_SERVICE_ENDPOINT': 'http://demo:5900',

    # numpy file
    'ENTITY_EMBEDDING_NPY': 'dkn_entity_embedding.npy',
    'CONTEXT_EMBEDDING_NPY': 'dkn_context_embedding.npy',
    'WORD_EMBEDDING_NPY': 'dkn_word_embedding.npy',

    # model file
    'MODEL_FILE': 'model.tar.gz',
}



# lastUpdate
localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

fill_array = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
action_model_type = 'action-model'
embedding_type = 'embedding'
pickle_type = 'inverted-list'


class Rank(service_pb2_grpc.RankServicer):

    def __init__(self):
        logging.info('__init__(self)...')
        # TODO load data for rank, get parameters from stream
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']

        # load pickle file to dict
        pickle_file_list = [MANDATORY_ENV_VARS['NEWS_ID_FEATURE']]
        self.reload_pickle_type(local_data_folder, pickle_file_list)

        init_model_file_name = [MANDATORY_ENV_VARS['MODEL_FILE']]
        self.reload_action_model(local_data_folder, init_model_file_name)

        embedding_npy_file_list = [MANDATORY_ENV_VARS['ENTITY_EMBEDDING_NPY'], MANDATORY_ENV_VARS['CONTEXT_EMBEDDING_NPY'], MANDATORY_ENV_VARS['WORD_EMBEDDING_NPY']]
        self.reload_embedding_files(local_data_folder, embedding_npy_file_list)

    def reload_action_model(self, file_path, file_list):
        logging.info('reload_embedding_files  strat')
        for file_name in file_list:
            model_path = file_path + file_name
            if os.path.isfile(model_path):
                logging.info('reload_action_model model_path {}'.format(model_path))
                self.model = self.reload_model(model_path)
            else:
                logging.info('model file is empty')     

    def reload_pickle_type(self, file_path, file_list):
        logging.info('reload_pickle_type  strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['NEWS_ID_FEATURE'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload news_id_news_feature_dict file {}'.format(pickle_path))
                    self.news_id_news_feature_dict = self.load_pickle(pickle_path)
                else:
                    logging.info('reload news_id_news_feature_dict_dict, file is empty')                   

    def reload_embedding_files(self, file_path, file_list):
        logging.info('reload_embedding_files  strat')
        for file_name in file_list:
            embedding_path = file_path + file_name
            logging.info('reload_embedding_files embedding_path {}'.format(embedding_path))
            if 'entity' in embedding_path:
                if os.path.isfile(embedding_path):
                    logging.info('reload entity_embed')
                    self.entity_embed = np.load(embedding_path)
                else:
                    logging.info('entity_embed is empty') 
            elif 'context' in embedding_path:
                if os.path.isfile(embedding_path):
                    logging.info('reload context_embed')
                    self.context_embed = np.load(embedding_path)
                else:
                    logging.info('context_embed is empty')                     
            elif 'word' in embedding_path: 
                if os.path.isfile(embedding_path):
                    logging.info('reload word_embed')
                    self.word_embed = np.load(embedding_path)
                    logging.info('word_embed size is {}'.format(np.shape(self.word_embed))) 
                else:
                    logging.info('word_embed is empty') 


    def reload_model(self, model_path):
        logging.info('reload_model start, model_path {}'.format(model_path))
        model_extract_dir = MANDATORY_ENV_VARS['MODEL_EXTRACT_DIR']
        self.extract(model_path, model_extract_dir)
        for name in glob.glob(os.path.join(model_extract_dir, '**', 'saved_model.pb'), recursive=True):
            logging.info("found model saved_model.pb in {} !".format(name))
            model_path = '/'.join(name.split('/')[0:-1])
        model = predictor.from_saved_model(model_path)
        logging.info("load model succeed!")
        return model 

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

    def extract(self, tar_path, target_path):
        tar = tarfile.open(tar_path, "r:gz")
        file_names = tar.getnames()
        for file_name in file_names:
            tar.extract(file_name, target_path)
        tar.close()               

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
        requestMessage = Any()
        request.dicts.Unpack(requestMessage)
        logging.info('Recieved notice requestMessage -> {}'.format(requestMessage))
        requestMessageJson = json.loads(requestMessage.value, encoding='utf-8')
        file_type = requestMessageJson['file_type']
        file_list = eval(requestMessageJson['file_list'])
        logging.info('file_type -> {}'.format(file_type))
        logging.info('file_list -> {}'.format(file_list))        
        self.check_files_ready(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list, 0) 
        if file_type == action_model_type:
            self.reload_action_model(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == embedding_type:
            self.reload_embedding_files(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == pickle_type:
            self.reload_pickle_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)

        logging.info('Re-initial rank service.')
        commonResponse = service_pb2.CommonResponse(code=0, description='Re-initialled with success')
        return commonResponse 

    def Status(self, request, context):
        logging.info('Status(self, request, context)...')
        status = Any()
        status.value =  json.dumps({
            "last_rank_result": localtime
        }).encode('utf-8')
        statusResponse = service_pb2.StatusResponse(code=0)
        statusResponse.status.Pack(status)
        return statusResponse  

    def Stop(self, request, context):
        logging.info('Stop(self, request, context)...')
        logging.info('Recieved singal -> %d', request.signal)
        commonResponse = service_pb2.CommonResponse(code=0, description='stop with doing nothing')
        return commonResponse 

    def RankProcess(self, request, context):
        logging.info('rank_process start')

        # Retrieve request data        
        reqDicts = Any()
        request.dicts.Unpack(reqDicts)
        reqData = json.loads(reqDicts.value, encoding='utf-8')
        user_id = reqData['user_id']
        recall_result = reqData['recall_result']
        logging.info('user_id -> {}'.format(user_id))
        logging.info('recall_result -> {}'.format(recall_result))

        #TODO need to call customer service to get real data
        # user_clicks_set = ['6553003847780925965','6553082318746026500','6522187689410691591']
        # user_clicks_set_redis = rCache.get_data_from_hash(user_id_click_dict, user_id)
        # if bool(user_clicks_set_redis):
        #     logging.info('user_clicks_set_redis {}'.format(user_clicks_set_redis))
        #     user_clicks_set = json.loads(user_clicks_set_redis, encoding='utf-8')
        user_clicks_set = []
        httpResp = requests.get(MANDATORY_ENV_VARS['DEMO_SERVICE_ENDPOINT']+'/api/v1/demo/click/'+user_id+'?curPage=0&pageSize=10')
        if httpResp.status_code == 200: 
            for var in httpResp.json()['data']:
                user_clicks_set.append(var.get('id'))

        logging.info("user click history {}".format(user_clicks_set))
        rank_result = self.generate_rank_result(recall_result, user_clicks_set)

        logging.info("rank result {}".format(rank_result))

        rankProcessResponseAny = Any()
        rankProcessResponseAny.value =  json.dumps(rank_result).encode('utf-8')
        rankProcessResponse = service_pb2.RankProcessResponse(code=0, description='rank process with success')
        rankProcessResponse.results.Pack(rankProcessResponseAny)        

        logging.info("rank process complete") 
        return rankProcessResponse

    def generate_rank_result(self, recall_result, user_clicks_set):
        logging.info('generate_rank_result start')
        news_words_index = []
        news_entity_index = []
        click_words_index = []
        click_entity_index = []

        for recall_item in recall_result:
            item_id = str(int(recall_item))
            logging.info('recall_item news id {}'.format(item_id))
            news_words_index.append(self.news_id_news_feature_dict[item_id]['words'])
            news_entity_index.append(self.news_id_news_feature_dict[item_id]['entities'])

            click_length = len(user_clicks_set)
            count = 0
            while click_length > 0 and count < 8:
                click_news_id = str(user_clicks_set[click_length - 1])
                logging.info('clicked_item_id {}'.format(click_news_id))
                logging.info('news_id_word_ids_dict {}'.format(self.news_id_news_feature_dict[click_news_id]['words']))
                logging.info('news_id_entity_ids_dict {}'.format(self.news_id_news_feature_dict[click_news_id]['entities']))
                click_words_index.append(self.news_id_news_feature_dict[click_news_id]['words'])
                click_entity_index.append(self.news_id_news_feature_dict[click_news_id]['entities'])
                click_length = click_length -1
                count = count + 1

            while count < 8:
                logging.info('add 0 because user_clicks_set length is less than 8')
                click_words_index.append(fill_array)
                click_entity_index.append(fill_array)
                count = count + 1
            # for clicked_item_id in temp_user_clicks_set:
            #     logging.info('clicked_item_id {}'.format(clicked_item_id))
            #     logging.info('news_id_word_ids_dict {}'.format(news_id_word_ids_dict[clicked_item_id]))
            #     logging.info('news_id_entity_ids_dict {}'.format(news_id_entity_ids_dict[clicked_item_id]))
            #     click_words_index.append(news_id_word_ids_dict[clicked_item_id])
            #     click_entity_index.append(news_id_entity_ids_dict[clicked_item_id])

        for idx in news_words_index:
            logging.info("news words len {} with array {}".format(len(idx), idx))
        for idx in news_entity_index:
            logging.info("news entities len {} with array {}".format(len(idx), idx))
        for idx in click_entity_index:
            logging.info("click entity len {} with array {}".format(len(idx), idx))
        for idx in click_words_index:
            logging.info("click word len {} with array {}".format(len(idx), idx))          

        news_words_index_np = np.array(news_words_index)
        news_entity_index_np = np.array(news_entity_index)
        click_words_index_np = np.array(click_words_index)
        click_entity_index_np = np.array(click_entity_index)        

        logging.info('start create input_dict')
        input_dict = {}
        input_dict['click_entities'] = self.entity_embed[click_entity_index_np]
        input_dict['click_words'] = self.word_embed[click_words_index_np]
        input_dict['news_entities'] = self.entity_embed[news_entity_index_np]
        input_dict['news_words'] = self.word_embed[news_words_index_np]
        logging.info("check input shape!")
        logging.info("input click entities shape {}".format(input_dict['click_entities'].shape))
        logging.info("input click words shape {}".format(input_dict['click_words'].shape))
        logging.info("input news entities shape {}".format(input_dict['news_entities'].shape))
        logging.info("input news words shape {}".format(input_dict['news_words'].shape))

        output = self.model(input_dict)

        logging.info('output {} from model'.format(output))

        output_prob = output['prob']
        rank_result = {}
        i = 0
        for recall_item in recall_result:
            rank_result[str(int(recall_item))] =  str(output_prob[i])
            i = i + 1

        return rank_result                                   

def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var]=os.environ.get(var)
    
def serve(plugin_name):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    service_pb2_grpc.add_RankServicer_to_server(Rank(), server)
    SERVICE_NAMES = (
        service_pb2.DESCRIPTOR.services_by_name['Rank'].full_name,
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