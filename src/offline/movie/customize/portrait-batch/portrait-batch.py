# portrait batch logic
import argparse
import logging
import os
import pickle

import boto3
import numpy as np
import pandas as pd
from deepmatch.layers import custom_objects
from tensorflow.python.keras.models import load_model
from tqdm import tqdm


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
    s3client.put_object(Body=str(content).encode("utf8"), Bucket=bucket, Key=key, ACL='bucket-owner-full-control')


parser = argparse.ArgumentParser(description="app inputs and outputs")
parser.add_argument("--bucket", type=str, help="s3 bucket")
parser.add_argument("--prefix", type=str, help="s3 input key prefix")
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

print(f"bucket:{bucket}, prefix:{prefix}")

s3client = boto3.client('s3')

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
# 行为数据加载
file_name_list = ['action.csv']
s3_folder = '{}/system/action-data/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# youtubednn模型相关文件
file_name_list = ['user_embeddings.h5']
s3_folder = '{}/model/recall/youtubednn/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# ub数据加载
file_name_list = ['raw_embed_user_mapping.pickle', 'raw_embed_item_mapping.pickle']
s3_folder = '{}/feature/action/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 用户画像数据加载
file_name_list = ['portrait.pickle']
s3_folder = '{}/feature/recommend-list/portrait'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 倒排列表的pickle文件
file_name_list = ['movie_id_movie_property_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# 加载用户数据
user_click_records = {}

data_mk = pd.read_csv('info/action.csv', sep='_!_',
                      names=['user_id', 'programId', 'action_type', 'action_value', 'timestamp'])

for reviewerID, hist in tqdm(data_mk[data_mk['action_value'] == 1].groupby('user_id')):
    pos_list = hist['programId'].tolist()
    user_click_records[reviewerID] = pos_list
# 加载pickle文件

file_to_load = open("info/movie_id_movie_property_dict.pickle", "rb")
dict_id_content = pickle.load(file_to_load)

file_to_load = open("info/raw_embed_item_mapping.pickle", "rb")
dict_item_mapping = pickle.load(file_to_load)

file_to_load = open("info/raw_embed_user_mapping.pickle", "rb")
dict_user_mapping = pickle.load(file_to_load)

# 加载模型
user_embedding_model = load_model('info/user_embeddings.h5', custom_objects)


def update_portrait_under_a_property(mt_content, mt_up, ratio):
    # decay logic
    if "''" in mt_up:
        del mt_up["''"]
    if '""' in mt_up:
        del mt_up['""']

    for k, v in mt_up.items():
        if k != 'recent':
            if mt_up[k]['mark'] != '1':
                mt_up[k]['score'] = mt_up[k]['score'] * ratio
            else:
                mt_up[k]['mark'] = '0'

    # update logic
    for ct in mt_content:
        if ct is not None and len(str(ct).strip()) > 0:
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
# 初始化用户画像
# 数据结构:
# 'language':{'xx':{'mark':,'score':},...'recent':['xx',score]}}
# 'embedding':{'review':xxx,'photo':xxx,'ub':xxx}
########################################
def initial_one_user_portrait():
    popularity_method_list = ['category', 'director',
                              'actor', 'language']
    current_user_portrait = {}
    for mt in popularity_method_list:
        current_user_portrait[mt] = {}
        current_user_portrait[mt]['recent'] = []
        current_user_portrait[mt]['recent'].append([])
        current_user_portrait[mt]['recent'].append(0.0)
    return current_user_portrait


def initial_user_portrait(user_list):
    user_data_frame = {}
    popularity_method_list = ['category', 'director',
                              'actor', 'language']
    for user in user_list:
        user_data_frame[str(user)] = initial_one_user_portrait()
    #     col_name = ['user_id']+popularity_method_list
    #     portrait_pddf = pd.DataFrame.from_dict(user_data_frame, orient='index',
    #                            columns=col_name)
    #     portrait_pddf = portrait_pddf.reset_index(drop=True)
    #     portrait_pddf.to_csv('info/portrait.csv')
    # save pickle file
    file_name = 'info/portrait.pickle'
    output_file = open(file_name, 'wb')
    pickle.dump(user_data_frame, output_file)
    output_file.close()
    # # backup original file
    # file_name = 'info/user_portrait_{}_raw.pickle'.format(user_name)
    # output_file = open(file_name, 'wb')
    # pickle.dump(current_user_portrait, output_file)
    # output_file.close()


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

    # 用户兴趣衰减系数
    decay_ratio = 0.8

    popularity_method_list = ['category', 'director',
                              'actor', 'language']

    for mt in popularity_method_list:
        if current_user_portrait.get(mt) is None:
            current_user_portrait[mt] = {
                "recent": [[], 0.0]
            }
        update_portrait_under_a_property(
            dict_id_content[current_read_item][mt], current_user_portrait[mt], decay_ratio)


#     print("updated user portrait {}".format(current_user_portrait))
#     # save pickle files
#     file_name = 'info/user_portrait_{}.pickle'.format(user_name)
#     output_file = open(file_name, 'wb')
#     pickle.dump(current_user_portrait, output_file)
#     output_file.close()


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


file_to_load = open("info/portrait.pickle", "rb")
dict_user_portrait = pickle.load(file_to_load)
print("update user portrait for batch users")
for user_id, input_item_list in user_click_records.items():
    if str(user_id) not in dict_user_mapping:
        print("Warning: cannot find user_id: {} in dict_user_mapping")
        continue
    print("user id {} item list {}".format(user_id, input_item_list))
    if dict_user_portrait.get(str(user_id)) is None:
        print("init portrait for user_id: {}".format(user_id))
        dict_user_portrait[str(user_id)] = initial_one_user_portrait()
    for ci in input_item_list:
        update_user_portrait_with_one_click(dict_user_portrait[str(user_id)], str(ci))
    try:
        dict_user_portrait[str(user_id)]['ub_embeddding'] = update_user_embedding(user_id, input_item_list)
    except Exception as e:
        logging.warning(repr(e))
        logging.warning("invalid user_id: {}".format(str(user_id)))
        del dict_user_portrait[str(user_id)]

# 存储和更新用户画像
file_name = 'info/portrait.pickle'
output_file = open(file_name, 'wb')
pickle.dump(dict_user_portrait, output_file)
output_file.close()
write_to_s3(file_name,
            bucket,
            "{}/feature/recommend-list/portrait/{}".format(prefix, file_name.split('/')[-1]))
