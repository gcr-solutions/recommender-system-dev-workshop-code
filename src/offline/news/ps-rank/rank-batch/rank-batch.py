from __future__ import print_function
import os
import sys
import math
import pickle
import json
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
#from pandarallel import pandarallel


# tqdm.pandas()
# pandarallel.initialize(progress_bar=True)
# bucket = os.environ.get("BUCKET_NAME", " ")
# raw_data_folder = os.environ.get("RAW_DATA", " ")
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# tqdm_notebook().pandas()

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

#pandarallel.initialize(use_memory_fs=False)

parser = argparse.ArgumentParser()
parser.add_argument('--bucket', type=str)
parser.add_argument('--prefix', type=str)
parser.add_argument("--region", type=str, help="aws region")

args, _ = parser.parse_known_args()
print("args:", args)

if args.region:
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix
region = args.region

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

s3client = boto3.client('s3')

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

#personalize 行为数据与配置文件加载
ps_config_file_name = ['ps_config.json']
ps_config_s3_folder = '{}/system/ps-config'.format(prefix)
sync_s3(ps_config_file_name, ps_config_s3_folder, local_folder)

#加载json配置文件
file_to_load = open("info/ps_config.json", "rb")
ps_config = json.load(file_to_load)
file_to_load.close()

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

    def __init__(self):
        self.personalize_runtime = boto3.client('personalize-runtime', region)

    def generate_rank_result_from_ps_rank(self, recall_result_pddf):
        recall_result = recall_result_pddf['news_id'].split('[')[1].split(']')[
            0].split(',')
        user_id = recall_result_pddf['user_id']
        print(recall_result)
        print('generate_rank_result using personalize rank model start')
        input_list = []
        for recall_item_raw in recall_result:
            recall_item = recall_item_raw.split("'")[1]
            recall_item = recall_item.split("'")[0]
            input_list.append(str(recall_item))
        response = self.personalize_runtime.get_personalized_ranking(
            campaignArn=ps_config['CampaignArn'],
            inputList=input_list,
            userId=user_id
        )
        rank_list = response['personalizedRanking']
        rank_result = []
        for rank_item in rank_list:
            if rank_item.__contains__('score'):
                rank_result.append({rank_item['itemId']: str(rank_item["score"])})
            else:
                rank_result.append({rank_item['itemId']: '0'})

        print(rank_result)
        return rank_result



batch_rank = Rank()

# 整理recall结果
data_input_pddf_dict = {}
data_input_pddf_dict['user_id'] = []
data_input_pddf_dict['news_id'] = []
for user_k, result_v in recall_batch_result.items():
    data_input_pddf_dict['user_id'].append(str(user_k))
    data_input_pddf_dict['news_id'].append(str(list(result_v.keys())))
data_input_pddf = pd.DataFrame.from_dict(data_input_pddf_dict)

data_input_pddf['rank_score'] = data_input_pddf.apply(
    batch_rank.generate_rank_result_from_ps_rank, axis=1)

rank_result = {}
for reviewerID, hist in tqdm(data_input_pddf.groupby('user_id')):
    score_list = hist['rank_score'].tolist()[0]
    print(score_list)
    id_score_dict = dict(pair for d in score_list for pair in d.items())
    sort_id_score_dict = {k: v for k, v in sorted(
        id_score_dict.items(), key=lambda item: item[1], reverse=True)}
    rank_result[reviewerID] = sort_id_score_dict

summary_result = {'model': 'ps-rank', 'data': rank_result}
file_name = 'info/rank_batch_result.pickle'
output_file = open(file_name, 'wb')
pickle.dump(summary_result, output_file)
output_file.close()

write_to_s3(file_name,
            bucket,
            '{}/feature/recommend-list/news/rank_batch_result.pickle'.format(prefix))
