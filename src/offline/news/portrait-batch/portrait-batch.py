from __future__ import print_function

import argparse
import os
import pickle

import boto3
import numpy as np
import pandas as pd
from tqdm import tqdm

# tqdm.pandas()
# pandarallel.initialize(progress_bar=True)
# bucket = os.environ.get("BUCKET_NAME", " ")
# raw_data_folder = os.environ.get("RAW_DATA", " ")

s3client = boto3.client('s3')

########################################
# 从s3同步数据
########################################
s3client = boto3.client('s3')


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


def s3_key_exists(bucket, key):
    try:
        res = s3client.head_object(
            Bucket=bucket,
            Key=key,
        )
    except Exception:
        return False
    if res:
        return True
    return False

parser = argparse.ArgumentParser()
parser.add_argument('--bucket', type=str)
parser.add_argument('--prefix', type=str)
args, _ = parser.parse_known_args()
bucket = args.bucket
prefix = args.prefix

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

s3client = boto3.client('s3')
local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
# 行为数据加载
file_name_list = ['action.csv']
s3_folder = '{}/system/action-data'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# # 用户画像数据加载


file_name_list = ['portrait.pickle']
s3_folder = '{}/feature/recommend-list/portrait'.format(prefix)
run_as_init = 0
portrait_file_key = os.path.join(s3_folder, file_name_list[0])
if s3_key_exists(bucket, portrait_file_key):
    sync_s3(file_name_list, s3_folder, local_folder)
    run_as_init = 0
else:
    print("Cannot find portrait_file_key: {}, run_as_init = 1".format(
        portrait_file_key))
    run_as_init = 1

# 倒排列表的pickle文件
file_name_list = ['news_id_news_property_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# 加载用户数据
file_to_load = open("info/news_id_news_property_dict.pickle", "rb")
dict_id_content = pickle.load(file_to_load)

user_click_records = {}
data_mk = pd.read_csv('info/action.csv', sep='_!_',
                      names=['user_id', 'news_id', 'timestamp', 'action_type', 'action'])
for reviewerID, hist in tqdm(data_mk[(data_mk['action'] == 1) & (data_mk['action_type'] == 1)].groupby('user_id')):
    pos_list = hist['news_id'].tolist()
    user_click_records[reviewerID] = pos_list


def update_portrait_under_a_property(mt_content, mt_up, ratio):
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
def update_user_portrait_with_one_click(current_user_portrait, current_read_item):
    #     # load user portrait for testing
    #     file_to_load = open("info/user_portrait_{}.pickle".format(user_name), "rb")
    #     current_user_portrait = pickle.load(file_to_load)
    #     print("load user portrait of the content is {}".format(current_user_portrait))

    if dict_id_content.get(current_read_item) is None:
        print("Warning: update_user_portrait_with_one_click"
              " cannot find {} in dict_id_content: news_id_news_property_dict.pickle".format(current_read_item))
        return

    # 用户兴趣衰减系数
    decay_ratio = 0.8

    popularity_method_list = ['keywords', 'type']

    for mt in popularity_method_list:
        update_portrait_under_a_property(
            dict_id_content[current_read_item][mt], current_user_portrait[mt], decay_ratio)


#     print("updated user portrait {}".format(current_user_portrait))
#     # save pickle files
#     file_name = 'info/user_portrait_{}.pickle'.format(user_name)
#     output_file = open(file_name, 'wb')
#     pickle.dump(current_user_portrait, output_file)
#     output_file.close()

def init_user_portrait():
    user_portrait = {}
    popularity_method_list = ['keywords', 'type']
    for mt in popularity_method_list:
        user_portrait[mt] = {}
        user_portrait[mt]['recent'] = []
        user_portrait[mt]['recent'].append([])
        user_portrait[mt]['recent'].append(0.0)

    return user_portrait


def update_user_embedding(user_id, input_item_list):
    #     file_to_load = open("info/user_portrait_{}.pickle".format(user_id), "rb")
    #     current_user_portrait = pickle.load(file_to_load)
    #     print("load user portrait of {}, the content is {}".format(
    #         user_name, current_user_portrait))

    # 映射用户的embedding
    # 构建适合模型的输入
    watch_list_len = 50
    map_input_item_list = np.array([[0] * watch_list_len])
    watch_len = len(input_item_list)
    map_user_id = dict_user_mapping[str(user_id)]
    for cnt, item in enumerate(input_item_list):
        if cnt < 50:
            map_input_item_list[0][cnt] = dict_item_mapping[str(item)]
    model_input = {}
    model_input['user_id'] = np.array([int(map_user_id)])
    model_input['hist_movie_id'] = map_input_item_list
    model_input['hist_len'] = np.array([watch_len])

    # 更新用户的embeddings
    #     print("model input {}".format(model_input))
    updated_user_embs = user_embedding_model.predict(
        model_input, batch_size=2 ** 12)

    #     current_user_portrait['ub_embed'] = updated_user_embs

    #     print("update user embeddings {}".format(updated_user_embs))

    return updated_user_embs


if run_as_init:
    dict_user_portrait = {}
else:
    file_to_load = open("info/portrait.pickle", "rb")
    dict_user_portrait = pickle.load(file_to_load)

print("update user portrait for batch users")
for user_id, input_item_list in user_click_records.items():
    print("user id {} item list {}".format(user_id, input_item_list))
    # update click history
    if not str(user_id) in dict_user_portrait:
        dict_user_portrait[str(user_id)] = init_user_portrait()

    dict_user_portrait[str(user_id)]['click_sets'] = input_item_list
    for ci in input_item_list:
        update_user_portrait_with_one_click(
            dict_user_portrait[str(user_id)], str(ci))


# 存储和更新用户画像
file_name = 'info/portrait.pickle'
output_file = open(file_name, 'wb')
pickle.dump(dict_user_portrait, output_file)
output_file.close()
write_to_s3(file_name,
            bucket,
            "{}/feature/recommend-list/portrait/{}".format(prefix, file_name.split('/')[-1]))
