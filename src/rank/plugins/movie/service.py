from concurrent import futures
import logging
import os
import json
import uuid
from datetime import datetime
import pickle
import requests
import sys
import pandas as pd
from tqdm import tqdm
import numpy as np
import time
import boto3

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
    'AWS_REGION': 'ap-northeast-1',

    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',
    'MOVIE_ID_MOVIE_FEATURE': 'movie_id_movie_feature_dict.pickle',
    'MODEL_EXTRACT_DIR': '/opt/ml/model/',

    # # numpy file
    # 'UB_ITEM_EMBEDDINGS_NPY': 'ub_item_embeddings.npy',

    # model file
    'MODEL_FILE': 'deepfm_model.tar.gz',

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,

    'PORTRAIT_SERVICE_ENDPOINT': 'http://portrait:5300',
    'S3_BUCKET': 'aws-gcr-rs-sol-dev-workshop-ap-northeast-1-466154167985',
    'S3_PREFIX': 'sample-data',
    'METHOD': 'customize',
    'PS_CONFIG': 'ps_config.json'
}



# lastUpdate
localtime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

fill_array = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
action_model_type = 'action-model'
embedding_type = 'embedding'
pickle_type = 'inverted-list'
json_type = 'ps-result'

personalize_runtime = boto3.client('personalize-runtime', MANDATORY_ENV_VARS['AWS_REGION'])

class Rank(service_pb2_grpc.RankServicer):

    def __init__(self):
        logging.info('__init__(self)...')
        # TODO load data for rank, get parameters from stream
        local_data_folder = MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']
        self.embed_dim = 32
        self.sparse_feature_size = 6

        # load pickle file to dict
        pickle_file_list = [MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_FEATURE']]
        self.reload_pickle_type(local_data_folder, pickle_file_list)

        init_model_file_name = [MANDATORY_ENV_VARS['MODEL_FILE']]
        self.reload_action_model(local_data_folder, init_model_file_name)

        # embedding_npy_file_list = [MANDATORY_ENV_VARS['UB_ITEM_EMBEDDINGS_NPY']]
        # self.reload_embedding_files(local_data_folder, embedding_npy_file_list)
        # Initial redis connection
        # global rCache
        # rCache = cache.RedisCache(host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])
        # logging.info('rank plugin init end!')

        json_file_list = [MANDATORY_ENV_VARS['PS_CONFIG']]
        self.reload_json_type(local_data_folder, json_file_list)

        self.personalize_runtime = boto3.client('personalize-runtime', MANDATORY_ENV_VARS['AWS_REGION'])

    def reload_action_model(self, file_path, file_list):
        logging.info('reload_model_files  start')
        for file_name in file_list:
            model_path = file_path + file_name
            if MANDATORY_ENV_VARS['MODEL_FILE'] in model_path:
                if os.path.isfile(model_path):
                    logging.info('reload_action_model model_path {}'.format(model_path))
                    self.model = self.reload_model(model_path)
                    # self.reload_model(model_path)
                else:
                    logging.info('model file is empty')     

    def reload_pickle_type(self, file_path, file_list):
        logging.info('reload_pickle_type  start')
        for file_name in file_list:
            pickle_path = file_path + file_name
            logging.info('reload_pickle_type pickle_path {}'.format(pickle_path))
            if MANDATORY_ENV_VARS['MOVIE_ID_MOVIE_FEATURE'] in pickle_path:
                if os.path.isfile(pickle_path):
                    logging.info('reload movie_id_movie_feature file {}'.format(pickle_path))
                    self.dict_id_feature_pddf = self.load_pickle_as_pddf(pickle_path)
                    self.dict_id_feature_pddf = self.dict_id_feature_pddf.drop_duplicates()
                    self.dict_id_feature_pddf['programId'] = self.dict_id_feature_pddf['programId'].astype(int)
                else:
                    logging.info('reload movie_id_movie_feature, file is empty')                   

    def reload_json_type(self, file_path, file_list):
        logging.info('reload_json_type start')
        for file_name in file_list:
            json_path = file_path + file_name
            logging.info('reload_json_type json_path {}'.format(json_path))
            if MANDATORY_ENV_VARS['PS_CONFIG'] in json_path:
                if os.path.isfile(json_path):
                    logging.info('reload ps_config file {}'.format(json_path))
                    self.ps_config = self.load_json_or_pickle(json_path)
                else:
                    logging.info('reload ps_config failed, file is empty')

    def reload_embedding_files(self, file_path, file_list):
        logging.info('reload_embedding_files  start')
        for file_name in file_list:
            embedding_path = file_path + file_name
            logging.info('reload_embedding_files embedding_path {}'.format(embedding_path))
            if 'ub_item' in embedding_path:
                if os.path.isfile(embedding_path):
                    logging.info('reload ub_item')
                    self.ub_item_embed = np.load(embedding_path)
                else:
                    logging.info('ub_item is empty') 
            # elif 'context' in embedding_path:
            #     if os.path.isfile(embedding_path):
            #         logging.info('reload context_embed')
            #         self.context_embed = np.load(embedding_path)
            #     else:
            #         logging.info('context_embed is empty')                     
            # elif 'word' in embedding_path: 
            #     if os.path.isfile(embedding_path):
            #         logging.info('reload word_embed')
            #         self.word_embed = np.load(embedding_path)
            #         logging.info('word_embed size is {}'.format(np.shape(self.word_embed))) 
            #     else:
            #         logging.info('word_embed is empty') 


    def reload_model(self, model_path):
        logging.info('reload_model start, model_path {}'.format(model_path))
        model_extract_dir = MANDATORY_ENV_VARS['MODEL_EXTRACT_DIR']
        self.extract(model_path, model_extract_dir)
        # TODO: check path
        for name in glob.glob(os.path.join(model_extract_dir, '**', 'saved_model.pb'), recursive=True):
            logging.info("found model saved_model.pb in {} !".format(name))
            model_path = '/'.join(name.split('/')[0:-1])
        model = predictor.from_saved_model(model_path)
        logging.info("load model succeed!")
        return model 

    def extract(self, tar_path, target_path):
        tar = tarfile.open(tar_path, "r")
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

    def load_json_or_pickle(self, file):
        logging.info("load_json_or_pickle start load {}".format(file))
        if os.path.isfile(file):
            infile = open(file, 'rb')
            if file.lower().endswith(".json"):
                dict = json.load(infile)
            else:
                dict = pickle.load(infile)
            infile.close()
            logging.info("load_json_or_pickle completed, key len:{}".format(len(dict)))
            return dict
        else:
            return {}

    def load_pickle_as_pddf(self, file):
        if os.path.isfile(file):
            # infile = open(file, 'rb')
            # dict = pickle.load(infile)
            # infile.close()
            pddf = pd.read_pickle(file)
            return pddf
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
        # elif file_type == embedding_type:
        #     self.reload_embedding_files(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == pickle_type:
            self.reload_pickle_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)
        elif file_type == json_type:
            self.reload_json_type(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)

        logging.info('Re-initial rank service.')
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
        status = Any()
        status.value =  json.dumps({
            # "redis_status": rCache.connection_status(),
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

    def modify_recall_result(self, dict_recall_result):
        # recall_result -> recall_result with feature
        data_input_pddf_dict = {}
        data_input_pddf_dict['userId'] = []
        data_input_pddf_dict['programId'] = []
        for user_k,result_v in dict_recall_result.items():
            for item_v in result_v.keys():
                data_input_pddf_dict['userId'].append(str(user_k))
                data_input_pddf_dict['programId'].append(str(item_v))
        data_input_pddf = pd.DataFrame.from_dict(data_input_pddf_dict)

        data_input_pddf['programId'] = data_input_pddf['programId'].astype(int)
        data_input_pddf = pd.merge(left=data_input_pddf, right=self.dict_id_feature_pddf, how='left',
                                left_on='programId', right_on='programId')
        return data_input_pddf

    def user_embed(self, x, user_portrait):
        if x in user_portrait.keys():
            #         print(user_portrait[x])
            return user_portrait[x]['ub_embeddding'][0]
        else:
            return [0] * 32

    def user_id_feat(self, x, i):
        return x[i]

    def add_user_feature(self, data_input_pddf, user_portrait):
        # user id feature - user embedding
        data_input_pddf['userid_feat'] = data_input_pddf['userId'].apply(lambda x: self.user_embed(x, user_portrait))
        for i in range(self.embed_dim):
            data_input_pddf['user_feature_{}'.format(i)] = data_input_pddf['userid_feat'].apply(lambda x: self.user_id_feat(x, i))
        return data_input_pddf

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

        if MANDATORY_ENV_VARS['METHOD'] == 'ps-rank':
            logging.info("ps-rank method: get rank result...")
            rank_result = self.generate_rank_result_from_ps_rank(user_id, recall_result)
        else:
            #TODO need to call customer service to get real data
            #TODO load portrait
            # Get user portrait from portrait service
            httpResp = requests.get(MANDATORY_ENV_VARS['PORTRAIT_SERVICE_ENDPOINT']+'/portrait/userid/'+user_id)
            if httpResp.status_code != 200:
                return service_pb2.MergeResultResponse(code=-1, description=('Failed to get portrait for -> {}').format(user_id))
            user_portrait = httpResp.json()
            # user_clicks_set = ['6553003847780925965','6553082318746026500','6522187689410691591']
            # user_clicks_set_redis = rCache.get_data_from_hash(user_id_click_dict, user_id)
            # if bool(user_clicks_set_redis):
            #     logging.info('user_clicks_set_redis {}'.format(user_clicks_set_redis))
            #     user_clicks_set = json.loads(user_clicks_set_redis, encoding='utf-8')

            recall_result_dict = {}
            recall_result_dict[user_id] = recall_result

            recall_result_with_item_feature = self.modify_recall_result(recall_result_dict)

            recall_result_with_user_item_feature = self.add_user_feature(recall_result_with_item_feature, user_portrait)

            rank_result = self.generate_rank_result(recall_result_with_user_item_feature)

        logging.info("rank result {}".format(rank_result))

        # rankProcessResponseValue = {
        #     'user_id': user_id,
        #     'rank_result': rank_result,
        #     'recall_result': recall_result
        # }

        rankProcessResponseAny = Any()
        rankProcessResponseAny.value =  json.dumps(rank_result).encode('utf-8')
        rankProcessResponse = service_pb2.RankProcessResponse(code=0, description='rank process with success')
        rankProcessResponse.results.Pack(rankProcessResponseAny)        

        logging.info("rank process complete") 
        return rankProcessResponse

    def generate_rank_result_from_ps_rank(self, user_id, recall_result):
        logging.info('generate_rank_result using personalize rank model start')
        response = self.personalize_runtime.get_personalized_ranking(
            campaignArn=self.ps_config['CampaignArn'],
            inputList=list(recall_result.keys()),
            userId=user_id
        )
        rank_list = response['personalizedRanking']
        logging.info("ps rank list:{}".format(rank_list))
        rank_result = {}
        for rank_item in rank_list:
            if rank_item.__contains__('score'):
                rank_result[rank_item['itemId']] = rank_item["score"]
            else:
                rank_result[rank_item['itemId']] = 0

        rank_summary = {'model': 'ps-rank', 'data': rank_result}
        return rank_summary

    def generate_rank_result(self, mk_test_data):
        logging.info('generate_rank_result start')
        dense_feature_size = self.embed_dim
        sparse_feature_size = self.sparse_feature_size
        for i in range(dense_feature_size):
            if i < self.embed_dim:
                mk_test_data['I{}'.format(i+1)] = mk_test_data['user_feature_{}'.format(i)]
                mk_test_data.drop(['user_feature_{}'.format(i)], axis=1)

        mk_test_data.drop(['userid_feat'],axis=1)
        mk_sparse_features = ['C' + str(i)for i in range(1, sparse_feature_size+1)]
        mk_dense_features = ['I'+str(i) for i in range(1, dense_feature_size+1)]
        mk_test_data[mk_sparse_features] = mk_test_data[mk_sparse_features].fillna('-1', )
        mk_test_data[mk_dense_features] = mk_test_data[mk_dense_features].fillna(0,)

        test_example = {}
        test_example['feat_ids'] = []
        test_example['feat_vals'] = []
        for row in mk_test_data.iterrows():
            row_content = row[1]
            feat_ids = []
            feat_vals = []
            for i,v in enumerate(mk_dense_features):
                feat_ids.append(i+1)
                feat_vals.append(row_content[v])
            for i,v in enumerate(mk_sparse_features):
                feat_ids.append(row_content[v])
                feat_vals.append(1)
            test_example['feat_ids'].append(feat_ids)
            test_example['feat_vals'].append(feat_vals)
        
        result = self.model(test_example)
        mk_pred_ans = result['prob']

        logging.info("finish rank the result is {}".format(mk_pred_ans))
        mk_test_data['rank_score'] = list(mk_pred_ans)
        # mk_test_data['rank_score'] = [v[0] for v in list(mk_pred_ans)]

        rank_result = {}
        for reviewerID, hist in tqdm(mk_test_data.groupby('userId')):
            candidate_list = hist['programId'].tolist()
            score_list = hist['rank_score'].tolist()
            id_score_dict = dict(zip(candidate_list, score_list))
            sort_id_score_dict = {k: v for k, v in sorted(id_score_dict.items(), key=lambda item: item[1], reverse=True)}
            rank_result[reviewerID] = sort_id_score_dict

        rank_summary = {'model': 'deepfm', 'data': rank_result}
        return rank_summary

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