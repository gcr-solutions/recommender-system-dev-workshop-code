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
import time
import argparse
import logging
import re
import service_impl

# tqdm.pandas()
# pandarallel.initialize(progress_bar=True)
# bucket = os.environ.get("BUCKET_NAME", " ")
# raw_data_folder = os.environ.get("RAW_DATA", " ")

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

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

s3client = boto3.client('s3')

out_s3_path = "s3://{}/{}/feature/content/inverted-list".format(bucket, prefix)

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
# 行为数据加载
file_name_list = ['action.csv']
s3_folder = '{}/system/action-data'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 用户画像数据加载
file_name_list = ['portrait.pickle']
s3_folder = '{}/feature/recommend-list/portrait'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 倒排列表的pickle文件
file_name_list = ['news_id_news_property_dict.pickle',
                  'news_type_news_ids_dict.pickle',
                  'news_entities_news_ids_dict.pickle',
                  'news_keywords_news_ids_dict.pickle',
                  'news_words_news_ids_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

file_name_list = ['recall_config.pickle']
s3_folder = '{}/feature/content/inverted-list'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# 加载pickle文件
file_to_load = open("info/news_id_news_property_dict.pickle", "rb")
dict_id_content = pickle.load(file_to_load)
print("length of news_id v.s. news_property {}".format(len(dict_id_content)))

file_to_load = open("info/news_type_news_ids_dict.pickle", "rb")
dict_type_id = pickle.load(file_to_load)
print("length of news_type v.s. news_ids {}".format(len(dict_type_id)))

file_to_load = open("info/news_entities_news_ids_dict.pickle", "rb")
dict_entities_id = pickle.load(file_to_load)
print("length of news_lanugage v.s. news_ids {}".format(len(dict_entities_id)))

file_to_load = open("info/news_keywords_news_ids_dict.pickle", "rb")
dict_keywords_id = pickle.load(file_to_load)
print("length of news_keywords v.s. news_ids {}".format(len(dict_keywords_id)))

file_to_load = open("info/news_words_news_ids_dict.pickle", "rb")
dict_words_id = pickle.load(file_to_load)
print("length of news_words v.s. news_ids {}".format(len(dict_words_id)))

file_to_load = open("info/recall_config.pickle", "rb")
recall_config = pickle.load(file_to_load)
print("config recall")

file_to_load = open("info/portrait.pickle", "rb")
user_portrait = pickle.load(file_to_load)
print("length of user_portrait {}".format(len(user_portrait)))

df_filter_action = pd.read_csv('info/action.csv', sep='_!_',
                               names=['user_id', 'news_id', 'timestamp', 'action_type', 'action'])

# 配置参数
config_dict = {}
recall_wrap = {}
recall_wrap['content'] = dict_id_content
recall_wrap['dict_wrap'] = {}
recall_wrap['dict_wrap']['type'] = dict_type_id
recall_wrap['dict_wrap']['entities'] = dict_entities_id
recall_wrap['dict_wrap']['words'] = dict_words_id
recall_wrap['dict_wrap']['keywords'] = dict_keywords_id
recall_wrap['config'] = recall_config
config_dict['recall_wrap'] = recall_wrap
# recall_wrap['ub_index'] = ub_faiss_index
# recall_wrap['ub_idx_mapping'] = ub_idx_mapping
# # 加载所有人的数据
# df_filter_action = pd.read_csv("info/action.csv", sep='\t')
# print("load {} action data".format(len(df_filter_action)))
# 初始化recall结果
recall_batch_result = {}
# print(config_dict)
recall_batch_function = service_impl.ServiceImpl()
for reviewerID, hist in tqdm(
        df_filter_action[(df_filter_action['action'] == 1) & (df_filter_action['action_type'] == 1)].groupby('user_id')):
    pos_list = hist['news_id'].tolist()
    config_dict['user_portrait'] = user_portrait[str(reviewerID)]
    # user_click_records[reviewerID] = pos_list
    recall_batch_result[str(reviewerID)] = recall_batch_function.merge_recall_result([str(elem) for elem in pos_list],
                                                                                     **config_dict)

# 存储recall的结果
file_name = "info/recall_batch_result.pickle"
out_file = open(file_name, 'wb')
pickle.dump(recall_batch_result, out_file)
out_file.close()

write_to_s3(file_name,
            bucket,
            '{}/feature/recommend-list/news/recall_batch_result.pickle'.format(prefix))
