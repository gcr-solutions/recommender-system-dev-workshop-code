from __future__ import print_function
import os
import sys
import math
import pickle
import boto3
import os
import numpy as np
import pandas as pd
from tqdm import tqdm
# from tqdm._tqdm_notebook import tqdm_notebook
import time
import argparse
import logging
import re
import tarfile
import glob
from tensorflow.contrib import predictor

# tqdm.pandas()
# pandarallel.initialize(progress_bar=True)
# bucket = os.environ.get("BUCKET_NAME", " ")
# raw_data_folder = os.environ.get("RAW_DATA", " ")
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# tqdm_notebook().pandas()
s3client = boto3.client('s3')

########################################
# 从s3同步数据
########################################


def sync_s3(file_name_list, s3_folder, local_folder):
    for f in file_name_list:
        print("file preparation: download src key {} to dst key {}".format(os.path.join(
            s3_folder, f), os.path.join(local_folder, f)))
        s3client.download_file(bucket, os.path.join(
            s3_folder, f), os.path.join(local_folder, f))


def write_to_s3(filename, bucket, key):
    print("upload s3://{}/{}".format(bucket, key))
    with open(filename, 'rb') as f:  # Read in binary mode
        # return s3client.upload_fileobj(f, bucket, key)
        return s3client.put_object(
            ACL='bucket-owner-full-control',
            Bucket=bucket,
            Key=key,
            Body=f
        )


def write_str_to_s3(content, bucket, key):
    print("write s3://{}/{}, content={}".format(bucket, key, content))
    s3client.put_object(Body=str(content).encode(
        "utf8"), Bucket=bucket, Key=key, ACL='bucket-owner-full-control')


default_bucket = 'aws-gcr-rs-sol-demo-ap-southeast-1-522244679887'
default_prefix = 'sample-data'
parser = argparse.ArgumentParser()
parser.add_argument('--bucket', type=str, default=default_bucket)
parser.add_argument('--prefix', type=str, default=default_prefix)
args, _ = parser.parse_known_args()
bucket = args.bucket
prefix = args.prefix

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

out_s3_path = "s3://{}/{}/feature/content/inverted-list".format(bucket, prefix)

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
# recall batch 结果记载
file_name_list = ['recall_batch_result.pickle']
s3_folder = '{}/feature/recommend-list/news'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 用户画像数据加载
file_name_list = ['portrait.pickle']
s3_folder = '{}/feature/recommend-list/portrait'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 倒排列表的pickle文件
file_name_list = ['news_id_news_property_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

file_name_list = ['news_id_news_feature_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# dkn模型文件下载
file_name_list = ['model.tar.gz']
s3_folder = '{}/model/rank/action/dkn/latest/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
file_name_list = ['dkn_entity_embedding.npy',
                  'dkn_context_embedding.npy', 'dkn_word_embedding.npy']
s3_folder = '{}/model/rank/content/dkn_embedding_latest/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# 加载pickle文件
file_to_load = open("info/recall_batch_result.pickle", "rb")
recall_batch_result = pickle.load(file_to_load)
file_to_load = open("info/portrait.pickle", "rb")
user_portrait = pickle.load(file_to_load)

# file_to_load = open("info/news_id_news_property_dict.pickle", "rb")
file_to_load = open("info/news_id_news_feature_dict.pickle", "rb")
dict_id_property_pddf = pickle.load(file_to_load)
print("length of news_id v.s. news_property {}".format(len(dict_id_property_pddf)))
# 解压缩dkn模型
tar = tarfile.open("info/model.tar.gz", "r")
file_names = tar.getnames()
for file_name in file_names:
    tar.extract(file_name, "info/")
tar.close
model_extract_dir = "info"


class Rank():

    def __init__(self, user_portrait, news_id_news_property):
        model_extract_dir = 'info'
        self.entity_embed = np.load("info/dkn_entity_embedding.npy")
        self.context_embed = np.load("info/dkn_context_embedding.npy")
        self.word_embed = np.load("info/dkn_word_embedding.npy")
        self.user_portrait = user_portrait
        self.news_id_news_property = news_id_news_property
        for name in glob.glob(os.path.join(model_extract_dir, '**', 'saved_model.pb'), recursive=True):
            logging.info("found model saved_model.pb in {} !".format(name))
            model_path = '/'.join(name.split('/')[0:-1])
        self.model = predictor.from_saved_model(model_path)
        self.fill_array = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

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

        # TODO need to call customer service to get real data
        user_clicks_set = ['6553003847780925965',
                           '6553082318746026500', '6522187689410691591']
        # user_clicks_set_redis = rCache.get_data_from_hash(user_id_click_dict, user_id)
        # if bool(user_clicks_set_redis):
        #     logging.info('user_clicks_set_redis {}'.format(user_clicks_set_redis))
        #     user_clicks_set = json.loads(user_clicks_set_redis, encoding='utf-8')

        rank_result = self.generate_rank_result(
            recall_result, self.news_id_entity_ids_dict, self.news_id_word_ids_dict, user_clicks_set)

        logging.info("rank result {}".format(rank_result))

        rankProcessResponseAny = Any()
        rankProcessResponseAny.value = json.dumps(rank_result).encode('utf-8')
        rankProcessResponse = service_pb2.RankProcessResponse(
            code=0, description='rank process with success')
        rankProcessResponse.results.Pack(rankProcessResponseAny)

        logging.info("rank process complete")
        return rankProcessResponse

    def generate_rank_result(self, recall_result_pddf):
        logging.info('generate_rank_result start')
        news_words_index = []
        news_entity_index = []
        click_words_index = []
        click_entity_index = []
        # debug for mingtong
        temp_user_clicks_set = []
        for i in range(8):
            temp_user_clicks_set.append('6552147830184608263')

        recall_result = recall_result_pddf['news_id'].split('[')[1].split(']')[
            0].split(',')
        user_id = recall_result_pddf['user_id']

        user_clicks_set = []
        if str(user_id) in self.user_portrait:
            user_clicks_set = self.user_portrait[str(user_id)]['click_sets']

        filter_recall_result = []
        for recall_item_raw in recall_result:
            recall_item = recall_item_raw.split("'")[1]
            recall_item = recall_item.split("'")[0]
            if self.news_id_news_property.get(str(recall_item)) is None:
                #logging.warning("cannot find {} in news_id_news_feature_dict".format(str(recall_item)))
                continue

            filter_recall_result.append(recall_item)
            logging.info('recall_item news id {}'.format(recall_item))
            logging.info('news_id_word_ids_dict {}'.format(
                self.news_id_news_property[str(recall_item)]['words']))
            logging.info('news_id_entity_ids_dict {}'.format(
                self.news_id_news_property[str(recall_item)]['entities']))

            news_words_index.append(
                self.news_id_news_property[str(recall_item)]['words'])
            news_entity_index.append(
                self.news_id_news_property[str(recall_item)]['entities'])

            click_length = len(user_clicks_set)
            count = 0
            while click_length > 0 and count < 8:
                click_index = user_clicks_set[click_length - 1]
                if str(click_index) not in self.news_id_news_property:
                    logging.warning('cannot find click_index: {} in news_id_news_property'.format(click_index))
                    continue
                logging.info('clicked_item_id {}'.format(click_index))
                logging.info('news_id_word_ids_dict {}'.format(
                    self.news_id_news_property[str(click_index)]['words']))
                logging.info('news_id_entity_ids_dict {}'.format(
                    self.news_id_news_property[str(click_index)]['entities']))
                click_words_index.append(
                    self.news_id_news_property[str(click_index)]['words'])
                click_entity_index.append(
                    self.news_id_news_property[str(click_index)]['entities'])
                click_length = click_length - 1
                count = count + 1

            while count < 8:
                logging.info(
                    'add 0 because user_clicks_set length is less than 8')
                click_words_index.append(self.fill_array)
                click_entity_index.append(self.fill_array)
                count = count + 1
            # for clicked_item_id in temp_user_clicks_set:
            #     logging.info('clicked_item_id {}'.format(clicked_item_id))
            #     logging.info('news_id_word_ids_dict {}'.format(news_id_word_ids_dict[clicked_item_id]))
            #     logging.info('news_id_entity_ids_dict {}'.format(news_id_entity_ids_dict[clicked_item_id]))
            #     click_words_index.append(news_id_word_ids_dict[clicked_item_id])
            #     click_entity_index.append(news_id_entity_ids_dict[clicked_item_id])

        for idx in news_words_index:
            logging.info(
                "news words len {} with array {}".format(len(idx), idx))
        for idx in news_entity_index:
            logging.info(
                "news entities len {} with array {}".format(len(idx), idx))
        for idx in click_entity_index:
            logging.info(
                "click entity len {} with array {}".format(len(idx), idx))
        for idx in click_words_index:
            logging.info(
                "click word len {} with array {}".format(len(idx), idx))

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
        logging.info("input click entities shape {}".format(
            input_dict['click_entities'].shape))
        logging.info("input click words shape {}".format(
            input_dict['click_words'].shape))
        logging.info("input news entities shape {}".format(
            input_dict['news_entities'].shape))
        logging.info("input news words shape {}".format(
            input_dict['news_words'].shape))

        output = self.model(input_dict)

        logging.info('output {} from model'.format(output))

        output_prob = output['prob']
        rank_result = []
        i = 0
        while i < len(output_prob):
            rank_result.append({
                filter_recall_result[i]: str(output_prob[i])
            })
            i = i + 1

        return rank_result


batch_rank = Rank(user_portrait, dict_id_property_pddf)

# 整理recall结果
data_input_pddf_dict = {}
data_input_pddf_dict['user_id'] = []
data_input_pddf_dict['news_id'] = []
for user_k, result_v in recall_batch_result.items():
    data_input_pddf_dict['user_id'].append(str(user_k))
    data_input_pddf_dict['news_id'].append(str(list(result_v.keys())))
data_input_pddf = pd.DataFrame.from_dict(data_input_pddf_dict)

data_input_pddf['rank_score'] = data_input_pddf.apply(
    batch_rank.generate_rank_result, axis=1)

rank_result = {}
for reviewerID, hist in tqdm(data_input_pddf.groupby('user_id')):
    score_list = hist['rank_score'].tolist()[0]
    id_score_dict = dict(pair for d in score_list for pair in d.items())
    sort_id_score_dict = {k: v for k, v in sorted(
        id_score_dict.items(), key=lambda item: item[1], reverse=True)}
    rank_result[reviewerID] = sort_id_score_dict

file_name = 'info/rank_batch_result.pickle'
output_file = open(file_name, 'wb')
pickle.dump(rank_result, output_file)
output_file.close()

write_to_s3(file_name,
            bucket,
            '{}/feature/recommend-list/news/rank_batch_result.pickle'.format(prefix))
