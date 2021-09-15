from __future__ import print_function
import os
import sys
import math
import pickle
import boto3
import os
import numpy as np
import kg
import encoding
import pandas as pd
# from tqdm import tqdm
import time
import argparse
import logging
import re

# tqdm.pandas()
# pandarallel.initialize(progress_bar=True)
# bucket = os.environ.get("BUCKET_NAME", " ")
# raw_data_folder = os.environ.get("RAW_DATA", " ")

s3client = boto3.client('s3')
MAX_ITEMS_IN_INVERTED_LIST = 20000

ONE_DAY_SECONDS = 24 * 3600


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


def calculate_popularity(df_action_input):
    df_filter_action = (df_action_input[df_action_input['action'] == 1])[
        ['news_id', 'timestamp', 'action_type', 'action']]
    max_timestamp = df_filter_action['timestamp'].max()

    weight_map = {
        "action": {"weight": 0.5, "seconds_before": 3 * 365 * ONE_DAY_SECONDS},
        "action_1hour": {"weight": 1.5, "seconds_before": 3600},
        "action_1day": {"weight": 1.5, "seconds_before": ONE_DAY_SECONDS},
        "action_7day": {"weight": 1.5, "seconds_before": 7 * ONE_DAY_SECONDS},
        "action_30day": {"weight": 0.75, "seconds_before": 30 * ONE_DAY_SECONDS},
    }

    for name in weight_map.keys():
        seconds_before = weight_map[name]['seconds_before']
        df = (df_filter_action[df_filter_action['timestamp'] > (max_timestamp - seconds_before)])[
            ['news_id', 'action_type', 'action']]
        df = df.groupby(['news_id', 'action_type']).sum()
        if name != 'action':
            df = df.rename(columns={
                "action": name
            })
        weight_map[name]["dataframe"] = df

    df_item_stats = weight_map['action']['dataframe']

    for name in weight_map.keys():
        if name == 'action':
            continue
        df = weight_map[name]["dataframe"]
        df_item_stats = pd.merge(df_item_stats, df, on=['news_id', 'action_type'], how="left")

    df_item_stats = df_item_stats.fillna(0)
    df_item_stats = df_item_stats.reset_index()

    for name in weight_map.keys():
        weight_value = weight_map[name]['weight']
        df_item_stats[name] = (df_item_stats[name] * weight_value / max(1, df_item_stats[name].abs().max())) * 10

    for col in weight_map.keys():
        if col != 'action':
            df_item_stats['action'] += df_item_stats[col]
            df_item_stats.drop(columns=[col], inplace=True)

    return df_item_stats


def load_pickle(file):
    with open(file, 'rb') as load_file:
        ret_val = pickle.load(load_file)
        print("loaded file {}, key len {}".format(file, len(ret_val)))
        return ret_val


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

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

s3client = boto3.client('s3')

meta_file_prefix = "{}/model/meta_files".format(prefix)

out_s3_path = "s3://{}/{}/feature/content/inverted-list".format(bucket, prefix)

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
# 行为/物品数据同步
file_name_list = ['action.csv']
s3_folder = '{}/system/popularity-action-data'.format(prefix)
run_as_init = 0

try:
    sync_s3(file_name_list, s3_folder, local_folder)
    run_as_init = 0
except Exception as e:
    run_as_init = 1

print("run_as_init:", run_as_init)

file_name_list = ['item.csv']
s3_folder = '{}/system/item-data'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

df_filter_item = pd.read_csv('info/item.csv', sep='_!_', names=[
    'news_id', 'type_code', 'type', 'title', 'keywords', 'popularity', 'new'])
df_filter_item.drop(columns=['popularity'], inplace=True)

print("len of item.csv {}".format(len(df_filter_item)))

news_id_news_feature_dict = {}
file_name_list = ["news_id_news_feature_dict.pickle"]
try:
    sync_s3(file_name_list, "{}/feature/content/inverted-list/".format(prefix), local_folder)
except Exception as e:
    print("Cannot find file {}".format(file_name_list[0]))

if os.path.exists("info/news_id_news_feature_dict.pickle"):
    news_id_news_feature_dict = load_pickle("info/news_id_news_feature_dict.pickle")

if run_as_init:
    df_item_stats = df_filter_item[['news_id']]
    df_item_stats['action_type'] = 1
    df_item_stats['action'] = 1
else:
    df_action_input = pd.read_csv('info/action.csv', sep='_!_',
                                  names=['user_id', 'news_id', 'timestamp', 'action_type', 'action'])
    print("len of action.csv {}".format(len(df_action_input)))
    df_item_stats = calculate_popularity(df_action_input)

df_item_stats['action'] = df_item_stats['action'] / max(df_item_stats['action'].abs().max(), 1) * 10

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

# generate dict_id_keywords for tfidf
dict_keywords_id = {}
for row in df_filter_item.iterrows():
    item_row = row[1]
    program_id = str(item_row['news_id'])
    for kw in str(item_row['keywords']).split(','):
        if kw not in dict_keywords_id.keys():
            dict_keywords_id[kw] = [program_id]
        else:
            dict_keywords_id[kw].append(program_id)
n_keyword_whole = len(dict_keywords_id)


def get_tfidf(category_property):
    if not category_property or str(category_property).lower() in ['nan', 'nr', '']:
        return [None]
    if not category_property:
        return [None]
    value = [item.strip() for item in category_property.split(',')]
    keywords_tfidf = {}
    for keyword in value:
        if keyword not in dict_keywords_id:
            continue
        current_score = 1 / \
                        len(value) * math.log(n_keyword_whole /
                                              len(dict_keywords_id[keyword]))
        keywords_tfidf[keyword] = current_score
    return keywords_tfidf


def get_category(category_property):
    if not category_property or str(category_property).lower() in ['nan', 'nr', '']:
        return [None]
    if not category_property:
        return [None]
    return [item.strip().lower() for item in category_property.split(',')]


def get_single_item(item):
    if not item or str(item).lower().strip() in ['nan', 'nr', '']:
        return [None]
    return [str(item).lower().strip()]


def get_entities(title):
    return model[title]


def single_dict(raw_dict, feat, item_id):
    if feat not in raw_dict.keys():
        raw_dict[feat] = [item_id]
    else:
        current_list = raw_dict[feat]
        current_list.append(item_id)
        raw_dict[feat] = current_list


def list_dict(raw_dict, feat_list, item_id, avoid=None):
    for feat in feat_list:
        if avoid != None and str(feat) == str(avoid):
            continue
        single_dict(raw_dict, feat, item_id)


def update_popularity(item_df, action_status_df):
    pd_merge_result = pd.merge(item_df, action_status_df, on="news_id", how="left").drop(
        columns=['action_type'])
    pd_merge_result = pd_merge_result.fillna(0)
    df_update = pd_merge_result.rename(
        columns={"action": "popularity"})
    df_update.loc[df_update.new == 1, ['popularity']] = 10.0

    return df_update


def sort_by_score(df):
    print("sort_by_score() enter, df.columns: {}".format(df.columns))
    df['popularity'].fillna(0, inplace=True)
    df_sorted = df.sort_values(by='popularity', ascending=False)
    print(
        "sort_by_score() return, df.columns: {}".format(df_sorted.columns))
    return df_sorted


def get_bucket_key_from_s3_path(s3_path):
    m = re.match(r"s3://(.*?)/(.*)", s3_path)
    return m.group(1), m.group(2)


def gen_pickle_files(item_df, action_stats_df):
    df_update = update_popularity(item_df, action_stats_df)
    print("df_update len: {}".format(len(df_update)))
    df_sort = sort_by_score(df_update)
    print("df_sort len: {}".format(len(df_sort)))

    news_id_news_property_dict = {}
    news_type_news_ids_dict = {}
    news_keywords_news_ids_dict = {}
    news_entities_news_ids_dict = {}
    news_words_news_ids_dict = {}
    row_count = 0
    total_count = len(df_sort)
    row_count_in_feature_dict = 0

    for row in df_sort.iterrows():
        item_row = row[1]
        program_id = str(item_row['news_id'])

        row_count += 1

        if row_count % 1000 == 0:
            print("process {}/{}".format(row_count, total_count))

        # current_entities = get_entities(item_row['title'])[1]
        # current_words = get_entities(item_row['title'])[0]

        if program_id in news_id_news_feature_dict:
            current_entities = news_id_news_feature_dict[program_id]['entities']
            current_words = news_id_news_feature_dict[program_id]['words']
            row_count_in_feature_dict += 1
        else:
            model_results = get_entities(item_row['title'])
            current_entities = model_results[1]
            current_words = model_results[0]
        # current_entities = [1] * 16
        # current_words = [1] * 16
        # if program_id == '6552382602181870087':
        #     model_results = get_entities(item_row['title'])
        #     current_entities = model_results[1]
        #     current_words = model_results[0]
        program_dict = {
            'title': get_single_item(item_row['title']),
            'type': get_single_item(item_row['type']),
            'keywords': get_category(item_row['keywords']),
            'tfidf': get_tfidf(item_row['keywords']),
            'entities': current_entities,
            'words': current_words
        }
        news_id_news_property_dict[program_id] = program_dict

        if row_count <= MAX_ITEMS_IN_INVERTED_LIST:
            list_dict(news_type_news_ids_dict, program_dict['type'], program_id)
            list_dict(news_keywords_news_ids_dict,
                      program_dict['keywords'], program_id)
            list_dict(news_entities_news_ids_dict,
                      program_dict['entities'], program_id, '0')
            list_dict(news_words_news_ids_dict, program_dict['words'], program_id, '0')

    result_dict = {
        'news_id_news_property_dict': news_id_news_property_dict,
        'news_type_news_ids_dict': news_type_news_ids_dict,
        'news_keywords_news_ids_dict': news_keywords_news_ids_dict,
        'news_entities_news_ids_dict': news_entities_news_ids_dict,
        'news_words_news_ids_dict': news_words_news_ids_dict
    }
    print("row_count_in_feature_dict: {}, total: {}".format(row_count_in_feature_dict, total_count))
    return result_dict


rd = gen_pickle_files(df_filter_item, df_item_stats)

bucket, out_prefix = get_bucket_key_from_s3_path(out_s3_path)
for dict_name, dict_val in rd.items():
    file_name = f'{dict_name}.pickle'
    # print("pickle =>", file_name)
    out_file = open(file_name, 'wb')
    pickle.dump(dict_val, out_file)
    out_file.close()
    # s3_url = S3Uploader.upload(file_name, out_s3_path)
    s3_url = write_to_s3(file_name, bucket, f'{out_prefix}/{file_name}')
    print("write {}".format(s3_url))
