# youtubednn嵌入部分模型训练逻辑
# 基础依赖
import argparse
import os
import pickle

import boto3
import faiss
import numpy as np
import pandas as pd
# 模型相关
from deepctr.feature_column import SparseFeat, VarLenSparseFeat
from deepmatch.models import *
from deepmatch.utils import recall_N
from deepmatch.utils import sampledsoftmaxloss
from tensorflow.python.keras import backend as K
from tensorflow.python.keras.models import Model, save_model
from tqdm import tqdm

from preprocess import gen_data_set, gen_model_input
import json

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

region = None
param_path = os.path.join('/opt/ml/', 'input/config/hyperparameters.json')
if os.path.exists(param_path):
    # running training job
    print("load param from {}".format(param_path))
    with open(param_path) as f:
        hp = json.load(f)
        print("hyperparameters:", hp)
        bucket = hp['bucket']
        prefix = hp['prefix']
        region = hp.get('region')
else:
    # running processing job
    parser = argparse.ArgumentParser(description="app inputs and outputs")
    parser.add_argument('--bucket', type=str)
    parser.add_argument('--prefix', type=str)
    parser.add_argument("--region", type=str, help="aws region")
    args, _ = parser.parse_known_args()
    print("args:", args)

    if args.region:
        region = args.region

    bucket = args.bucket
    prefix = args.prefix

if region:
    print("region:", region)
    boto3.setup_default_session(region_name=region)

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
# encode映射数据
file_name_list = ['raw_embed_item_mapping.pickle', 'raw_embed_user_mapping.pickle']
s3_folder = '{}/feature/action/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 加载pickle文件
file_to_load = open("info/raw_embed_item_mapping.pickle", "rb")
raw_embed_item_mapping = pickle.load(file_to_load)
file_to_load = open("info/raw_embed_user_mapping.pickle", "rb")
raw_embed_user_mapping = pickle.load(file_to_load)

user_ids = pd.DataFrame(raw_embed_user_mapping.keys(), columns=['user_id'])
user_ids = user_ids.astype('str')
item_ids = pd.DataFrame(raw_embed_item_mapping.keys(), columns=['movie_id'])
item_ids = item_ids.astype('str')

# 加载所有人的数据
data_mk = pd.read_csv('info/action.csv', sep='_!_',
                      names=['user_id', 'movie_id', 'action_type', 'action_value', 'timestamp'])

data_tt = data_mk.rename(columns={'action_value': 'rating'})
data_tt = data_tt.astype('str')
print("before join user_ids/item_ids, len data_tt:", len(data_tt))

data_tt = pd.merge(data_tt, user_ids, how='inner', on=['user_id'])
data_tt = pd.merge(data_tt, item_ids, how='inner', on=['movie_id'])

print("after join user_ids/item_ids, len data_tt:", len(data_tt))

data_tt_click = data_tt[data_tt['rating'] == '1']
data_tt_exp = data_tt[data_tt['rating'] == '0']
print('click len {} and exp len {}, click rate {}, {} movies'.format(len(data_tt_click), len(data_tt_exp),
                                                                     float(len(data_tt_click) / len(data_tt)),
                                                                     len(data_tt['movie_id'].unique())))


features = ['user_id', 'movie_id']
map_dicts = [raw_embed_user_mapping, raw_embed_item_mapping]
feature_max_idx = {}
for feature, map_dict in zip(features, map_dicts):
    #     lbe = LabelEncoder()
    #     data_tt[feature] = lbe.fit_transform(data_tt[feature]) + 1
    data_tt[feature + "_encode"] = data_tt[feature].apply(lambda x: map_dict[x])
    feature_max_idx[feature] = data_tt[feature + "_encode"].max() + 1

data_tt.drop(columns=["user_id", "movie_id"], inplace=True)
data_tt = data_tt.rename(columns={
    "user_id_encode": "user_id",
    "movie_id_encode": "movie_id"
})

item_profile = list(raw_embed_item_mapping.keys())
item_profile_encode = []
for ele in item_profile:
    item_profile_encode.append(raw_embed_item_mapping[ele])

count_thred = 2
data_tt_filter = data_tt[data_tt['rating'] == '1'].groupby(['movie_id']).filter(lambda x: len(x) > count_thred)
pass_item_pddf = data_tt_filter.drop_duplicates('movie_id')[['movie_id', 'rating']]

data_tt_click = data_tt[data_tt['rating'] == '1']
keys = list(pass_item_pddf.columns.values)
i1 = data_tt_click.set_index(keys).index
i2 = pass_item_pddf.set_index(keys).index
data_tt_click = data_tt_click[i1.isin(i2)]

# data = pd.read_csvdata = pd.read_csv("./movielens_sample.txt")
sparse_features = ["movie_id", "user_id"]
SEQ_LEN = 50
negsample = 5

# 1.Label Encoding for sparse features,and process sequence features with `gen_date_set` and `gen_model_input`
user_profile = data_tt[["user_id"]].drop_duplicates('user_id')

# item_profile = data_tt.drop_duplicates('movie_id')
# item_profile = data[["movie_id"]].drop_duplicates('movie_id')

user_profile.set_index("user_id", inplace=True)

user_item_list = data_tt.groupby("user_id")['movie_id'].apply(list)

# train_set, test_set = gen_data_set(data_tt_click, negsample, data_tt['movie_id'].unique())
train_set, test_set = gen_data_set(data_tt_click, negsample, np.array(item_profile_encode))

train_model_input, train_label = gen_model_input(train_set, user_profile, SEQ_LEN)
test_model_input, test_label = gen_model_input(test_set, user_profile, SEQ_LEN)

# 2.count #unique features for each sparse field and generate feature config for sequence feature

embedding_dim = 32

user_feature_columns = [SparseFeat('user_id', feature_max_idx['user_id'], 16),
                        VarLenSparseFeat(SparseFeat('hist_movie_id', feature_max_idx['movie_id'], embedding_dim,
                                                    embedding_name="movie_id"), SEQ_LEN, 'mean', 'hist_len'),
                        ]

item_feature_columns = [SparseFeat('movie_id', feature_max_idx['movie_id'], embedding_dim)]

# 3.Define Model and train

K.set_learning_phase(True)

import tensorflow as tf

if tf.__version__ >= '2.0.0':
    tf.compat.v1.disable_eager_execution()

model = YoutubeDNN(user_feature_columns, item_feature_columns, num_sampled=100,
                   user_dnn_hidden_units=(128, 64, embedding_dim))
# model = MIND(user_feature_columns,item_feature_columns,dynamic_k=False,p=1,k_max=2,num_sampled=100,user_dnn_hidden_units=(128,64, embedding_dim))

model.compile(optimizer="adam", loss=sampledsoftmaxloss)  # "binary_crossentropy")

history = model.fit(train_model_input, train_label,  # train_label,
                    batch_size=512, epochs=300, verbose=1, validation_split=0.0, )

# 4. Generate user features for testing and full item features for retrieval
test_user_model_input = test_model_input
# all_item_model_input = {"movie_id": item_profile['movie_id'].values,}
all_item_model_input = {"movie_id": np.array(item_profile_encode), }

user_embedding_model = Model(inputs=model.user_input, outputs=model.user_embedding)
item_embedding_model = Model(inputs=model.item_input, outputs=model.item_embedding)

user_embs = user_embedding_model.predict(test_user_model_input, batch_size=2 ** 12)
# user_embs = user_embs[:, i, :]  # i in [0,k_max) if MIND
item_embs = item_embedding_model.predict(all_item_model_input, batch_size=2 ** 12)

# print(user_embs.shape)
# print(item_embs.shape)
# print(user_embs)

index = faiss.IndexFlatIP(embedding_dim)
# faiss.normalize_L2(item_embs)
index.add(item_embs)
# faiss.normalize_L2(user_embs)
D, I = index.search(np.ascontiguousarray(user_embs), 50)
s = []
hit = 0
test_cnt = 0

test_true_label = {line[0]: [line[2]] for line in test_set}

for i, uid in tqdm(enumerate(test_user_model_input['user_id'])):
    #     try:
    pred = [item_profile_encode[x] for x in I[i]]
    filter_item = None
    recall_score = recall_N(test_true_label[uid], pred, N=50)
    s.append(recall_score)
    #         print(test_true_label[uid])
    #         print(pred)
    #         break
    if test_true_label[uid][0] in pred:
        #             if test_cnt < 10:
        #                 print("input {} pred {} and label {}".format(I[i], pred, test_true_label[uid]))
        #                 test_cnt = test_cnt + 1
        hit += 1
#         if recall_score > 0:
#             print("input {} pred {} and label {}".format(I[i], pred, test_true_label[uid]))
#             test_cnt = test_cnt + 1
#     except:
#         print(i)
print("")
print("recall", np.mean(s))
print("hit rate", hit / len(test_user_model_input['user_id']))

# 存储/更新用户嵌入模型
file_name = 'info/user_embeddings.h5'
save_model(user_embedding_model, file_name)
write_to_s3(file_name, bucket, "{}/model/recall/youtubednn/{}".format(prefix, file_name.split('/')[-1]))

# 存储/更新faiss index
file_name = 'info/ub_item_vector.index'
faiss.write_index(index, file_name)
write_to_s3(file_name, bucket, "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))

# 存储/更新物品embedding npy
file_name = 'info/ub_item_embeddings.npy'
with open(file_name, 'wb') as f:
    np.save(f, item_embs)
write_to_s3(file_name, bucket, "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))
