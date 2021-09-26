from concurrent import futures
import logging
import os
import json
from datetime import datetime
import numpy as np
import pickle
import sys
import time

from google.protobuf import any_pb2
import grpc
from grpc_reflection.v1alpha import reflection
from deepmatch.layers import custom_objects
import tensorflow as tf
from tensorflow.python.keras.backend import set_session
from tensorflow.python.keras.models import load_model

import cache

import service_pb2
import service_pb2_grpc

# Environments for service
MANDATORY_ENV_VARS = {
    'AWS_REGION': 'ap-northeast-1',
    'USER_EMBEDDINGS_H5': 'user_embeddings.h5',

    'RAW_EMBED_USER_MAPPING': 'raw_embed_user_mapping.pickle',
    'RAW_EMBED_ITEM_MAPPING': 'raw_embed_item_mapping.pickle',

    'MOVIE_ID_MOVIE_PROPERTY': 'movie_id_movie_property_dict.pickle',

    'PORTRAIT_BATCH': 'portrait.pickle',

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
}

pickle_type = 'inverted-list'
model_type = 'action-model'
# lastUpdate
getLastCall = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
updateLastCall = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

class Portrait(service_pb2_grpc.PortraitServicer):

    def __init__(self):
        logging.info('__init__(self)...')

        global sess
        global graph
        sess = tf.Session()
        graph = tf.get_default_graph()

        # Load index model for similarity searching
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        # logging.info('Files -> %s in %s', local_data_folder, os.listdir(local_data_folder))
        pickle_file_list = []
        pickle_file_list.append(MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_PROPERTY'])
        pickle_file_list.append(MANDATORY_ENV_VARS['RAW_EMBED_ITEM_MAPPING'])
        pickle_file_list.append(MANDATORY_ENV_VARS['RAW_EMBED_USER_MAPPING'])

        # TODO:add time-stamp to mark new/old recordings
        pickle_file_list.append(MANDATORY_ENV_VARS['PORTRAIT_BATCH'])

        self.reload_pickle_file(local_data_folder, pickle_file_list)

        init_model_file_name = [MANDATORY_ENV_VARS['USER_EMBEDDINGS_H5']]
        self.reload_action_model(local_data_folder, init_model_file_name)


    def reload_pickle_file(self, file_path, file_list):
        logging.info('reload_pickle_file  strat')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_PROPERTY'] in pickle_path:
                logging.info('reload movie_id_movie_property file {}'.format(pickle_path))
                self.movie_id_movie_property_dict = self.load_pickle(pickle_path)
            if MANDATORY_ENV_VARS['RAW_EMBED_ITEM_MAPPING']in pickle_path:
                logging.info('reload raw_embed_item_mapping file {}'.format(pickle_path))
                self.raw_embed_item_mapping_dict = self.load_pickle(pickle_path)
                logging.info('raw_embed_item_mapping {}'.format(self.raw_embed_item_mapping_dict)) 
            if MANDATORY_ENV_VARS['RAW_EMBED_USER_MAPPING'] in pickle_path:
                logging.info('reload file {}'.format(pickle_path))
                self.raw_embed_user_mapping_dict = self.load_pickle(pickle_path)                     
                logging.info('raw_embed_user_mapping {}'.format(self.raw_embed_user_mapping_dict)) 
            if MANDATORY_ENV_VARS['PORTRAIT_BATCH'] in pickle_path:
                logging.info('batch reload portrait file {}'.format(pickle_path))
                self.batch_reload_pickle_files(pickle_path)
                # self.raw_embed_user_mapping_dict = self.load_pickle(pickle_path)                     
                logging.info('successful batch reload portrait file')
                # logging.info('raw_embed_user_mapping {}'.format(self.raw_embed_user_mapping_dict)) 

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
                # logging.info('user_portrait -> userid: %s, portrait: %s', k, v)
                rCache.save_user_portrait(k, json.dumps(v, cls=NumpyEncoder).encode('utf-8'))
                logging.info('Saving has done.')

            return dict
        else:
            return {}

    def reload_action_model(self, file_path, file_list):
        logging.info('reload_model_files  start')
        for file_name in file_list:
            model_path = file_path + file_name
            if MANDATORY_ENV_VARS['USER_EMBEDDINGS_H5'] in model_path:
                if os.path.isfile(model_path):
                    logging.info('reload_action_model model_path {}'.format(model_path))
                    set_session(sess)
                    self.user_embedding_model = load_model(model_path, custom_objects)
                    # self.reload_model(model_path)
                else:
                    logging.info('model file is empty')     

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
        if file_type == model_type:
            self.reload_action_model(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
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
        # 用户兴趣衰减系数
        decay_ratio = 0.8

        popularity_method_list = ['category', 'director',
                                'actor', 'language']

        logging.info('update logic -> current_user_portrait %s', current_user_portrait)       

        for mt in popularity_method_list:
            self.update_portrait_under_a_property(
                self.movie_id_movie_property_dict[current_read_item][mt], current_user_portrait[mt], decay_ratio)

    def update_user_embedding(self, user_id, input_item_list):
        #     file_to_load = open("info/user_portrait_{}.pickle".format(user_id), "rb")
        #     current_user_portrait = pickle.load(file_to_load)
        #     print("load user portrait of {}, the content is {}".format(
        #         user_name, current_user_portrait))

        # 映射用户的embedding
        # 构建适合模型的输入
        watch_list_len = 50
        map_input_item_list = np.array([[0] * watch_list_len])
        watch_len = len(input_item_list)

        ### TODO 需要获取当前最大用户编号，自动增加编号
        map_user_id = 0
        logging.info("raw_embed_user_mapping_dict length: {}".format(len(self.raw_embed_user_mapping_dict)))
        if str(user_id) in self.raw_embed_user_mapping_dict:
            map_user_id = self.raw_embed_user_mapping_dict[str(user_id)]
        for cnt, item in enumerate(input_item_list):
            if cnt < 50:
                map_input_item_list[0][cnt] = self.raw_embed_item_mapping_dict[str(item)]
        model_input = {}
        model_input['user_id'] = np.array([int(map_user_id)])
        model_input['hist_movie_id'] = map_input_item_list
        model_input['hist_len'] = np.array([watch_len])

        # 更新用户的embeddings
        #     print("model input {}".format(model_input))
        updatad_user_embs = None
        with graph.as_default():
            set_session(sess)
            updated_user_embs = self.user_embedding_model.predict(
                model_input, batch_size=2 ** 12)

        #     current_user_portrait['ub_embed'] = updated_user_embs

        #     print("update user embeddings {}".format(updated_user_embs))

        return updated_user_embs

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
            popularity_method_list = ['category', 'director', 'actor', 'language']
            for mt in popularity_method_list:
                user_portrait[mt] = {}
                user_portrait[mt]['recent'] = []
                user_portrait[mt]['recent'].append([])
                user_portrait[mt]['recent'].append(0.0)

        dict_user_portrait = {}
        dict_user_portrait[str(user_id)] = user_portrait

        logging.info('dict_user_portrait: {}'.format(dict_user_portrait))
        user_click_records = {}
        user_click_records[user_id] = clicked_news_ids
        for user_id, input_item_list in user_click_records.items():
            print("user id {} item list {}".format(user_id, input_item_list))
            for ci in input_item_list:
                self.update_user_portrait_with_one_click(dict_user_portrait[str(user_id)], str(ci))
            dict_user_portrait[str(user_id)]['ub_embeddding'] = self.update_user_embedding(user_id, input_item_list)
            
        user_portrait = dict_user_portrait[str(user_id)]
        # Save into Redis
        logging.info('user_portrait -> %s', user_portrait)
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return json.JSONEncoder.default(self, obj)
        if bool(user_portrait):
            logging.info('Save user_portrait into Redis.')
            rCache.save_user_portrait(user_id, json.dumps(user_portrait, cls=NumpyEncoder).encode('utf-8'))
            logging.info('Saving has done.')

        ###
        logging.info('update_portrait() has done.')
        portraitResponseAny = any_pb2.Any()
        portraitResponseAny.value =  json.dumps(user_portrait, cls=NumpyEncoder).encode('utf-8')
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