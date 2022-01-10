from __future__ import print_function

# from tqdm import tqdm
import argparse
import os
import pickle

import boto3
import numpy as np
import pandas as pd

import encoding
import kg

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

parser = argparse.ArgumentParser()
parser.add_argument('--bucket', type=str)
parser.add_argument('--prefix', type=str)
parser.add_argument("--region", type=str, help="aws region")
args, _ = parser.parse_known_args()
print("args:", args)
region = None
if args.region:
    region = args.region
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

s3client = boto3.client('s3')


out_s3_path = "s3://{}/{}/feature/content/inverted-list".format(bucket, prefix)

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)

file_name_list = ['complete_dkn_word_embedding.npy']
s3_folder = '{}/model/rank/content/dkn_embedding_latest/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

file_name_list = ['item.csv']
s3_folder = '{}/system/item-data'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

file_name_list = ['entities_dbpedia.dict', 'relations_dbpedia.dict',
                  'kg_dbpedia.txt', 'entities_dbpedia_train.dict',
                  'relations_dbpedia_train.dict', 'kg_dbpedia_train.txt',
                  ]
s3_folder = '{}/model/meta_files/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

df_filter_item = pd.read_csv('info/item.csv', sep='_!_',
                             names=['news_id', 'type_code', 'type', 'title', 'keywords', 'popularity', 'new'])

complete_dkn_word_embed = np.load("info/complete_dkn_word_embedding.npy")

# prepare model for batch process
meta_file_prefix = "{}/model/meta_files".format(prefix)
os.environ['GRAPH_BUCKET'] = bucket
os.environ['KG_DBPEDIA_KEY'] = '{}/kg_dbpedia.txt'.format(meta_file_prefix)
os.environ['KG_ENTITY_KEY'] = '{}/entities_dbpedia.dict'.format(
    meta_file_prefix)
os.environ['KG_RELATION_KEY'] = '{}/relations_dbpedia.dict'.format(
    meta_file_prefix)
os.environ['KG_DBPEDIA_TRAIN_KEY'] = '{}/kg_dbpedia_train.txt'.format(
    meta_file_prefix)
os.environ['KG_ENTITY_TRAIN_KEY'] = '{}/entities_dbpedia_train.dict'.format(
    meta_file_prefix)
os.environ['KG_RELATION_TRAIN_KEY'] = '{}/relations_dbpedia_train.dict'.format(
    meta_file_prefix)
os.environ['KG_ENTITY_INDUSTRY_KEY'] = '{}/entity_industry.txt'.format(
    meta_file_prefix)
os.environ['KG_VOCAB_KEY'] = '{}/vocab.json'.format(meta_file_prefix)
os.environ['DATA_INPUT_KEY'] = ''
os.environ['TRAIN_OUTPUT_KEY'] = '{}/model/rank/content/dkn_embedding_latest/'.format(
    prefix)

kg_path = os.environ['GRAPH_BUCKET']
dbpedia_key = os.environ['KG_DBPEDIA_KEY']
entity_key = os.environ['KG_ENTITY_KEY']
relation_key = os.environ['KG_RELATION_KEY']
dbpedia_train_key = os.environ['KG_DBPEDIA_TRAIN_KEY']
entity_train_key = os.environ['KG_ENTITY_TRAIN_KEY']
relation_train_key = os.environ['KG_RELATION_TRAIN_KEY']
entity_industry_key = os.environ['KG_ENTITY_INDUSTRY_KEY']
vocab_key = os.environ['KG_VOCAB_KEY']
data_input_key = os.environ['DATA_INPUT_KEY']
train_output_key = os.environ['TRAIN_OUTPUT_KEY']

env = {
    'GRAPH_BUCKET': kg_path,
    'KG_DBPEDIA_KEY': dbpedia_key,
    'KG_ENTITY_KEY': entity_key,
    'KG_RELATION_KEY': relation_key,
    'KG_DBPEDIA_TRAIN_KEY': dbpedia_train_key,
    'KG_ENTITY_TRAIN_KEY': entity_train_key,
    'KG_RELATION_TRAIN_KEY': relation_train_key,
    'KG_ENTITY_INDUSTRY_KEY': entity_industry_key,
    'KG_VOCAB_KEY': vocab_key,
    'DATA_INPUT_KEY': data_input_key,
    'TRAIN_OUTPUT_KEY': train_output_key
}

print("Kg env: {}".format(env))
graph = kg.Kg(env, region=region)  # Where we keep the model when it's loaded
model = encoding.encoding(graph, env, region=region)

news_id_news_feature_dict = {}
map_words = {}
map_entities = {}


def analyze_map(raw_idx, map_dict, filter_idx):
    for idx in raw_idx:
        if idx == 0:
            filter_idx.append(0)
        else:
            if idx not in map_dict.keys():
                map_dict[idx] = len(map_dict) + 1
            filter_idx.append(map_dict[idx])


count = 0
total = len(df_filter_item)

for row in df_filter_item.iterrows():
    count += 1
    if count % 1000 == 0:
        print("{}/{}".format(count, total))

    item_row = row[1]
    program_id = str(item_row['news_id'])
    title_result = model[item_row['title']]
    current_words = title_result[0]
    current_entities = title_result[1]
    filter_words = []
    filter_entities = []
    analyze_map(current_words, map_words, filter_words)
    analyze_map(current_entities, map_entities, filter_entities)
    # filter entities & filter words
    program_dict = {
        'entities': filter_entities,
        'words': filter_words
    }
    news_id_news_feature_dict[program_id] = program_dict

file_name = 'info/news_id_news_feature_dict_for_train.pickle'
out_file = open(file_name, 'wb')
pickle.dump(news_id_news_feature_dict, out_file)
out_file.close()
# s3_url = S3Uploader.upload(file_name, out_s3_path)
s3_url = write_to_s3(file_name, bucket,
                     '{}/feature/content/inverted-list/news_id_news_feature_dict_for_train.pickle'.format(prefix))
