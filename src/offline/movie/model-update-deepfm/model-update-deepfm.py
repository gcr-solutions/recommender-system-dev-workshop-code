# deepfm模型训练逻辑
# 基础依赖
import argparse
import os
import pickle
import random
import subprocess
import json

import boto3
import numpy as np
import pandas as pd
from deepmatch.layers import custom_objects
from sklearn.model_selection import train_test_split
# 模型相关
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


def run_script(script):
    print("run_script: '{}'".format(script))
    re_code, out_msg = subprocess.getstatusoutput([script])
    print("run_script re_code:", re_code)
    for line in out_msg.split("\n"):
        print(line)
    if re_code != 0:
        raise Exception(out_msg)


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
file_name_list = ['train_action.csv']
s3_folder = '{}/system/action-data/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# youtubednn模型数据加载
file_name_list = ['raw_embed_item_mapping.pickle', 'raw_embed_user_mapping.pickle']
s3_folder = '{}/feature/action/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
file_name_list = ['user_embeddings.h5']
s3_folder = '{}/model/recall/youtubednn/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 倒排列表的pickle文件
file_name_list = ['movie_id_movie_feature_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# 加载所有人的数据
action_data_pddf = pd.read_csv('info/train_action.csv', sep='_!_',
                               names=['user_id', 'item_id', 'action_type', 'action_value', 'timestamp'])
print("load {} action data".format(len(action_data_pddf)))

# 加载pickle文件
file_to_load = open("info/movie_id_movie_feature_dict.pickle", "rb")
dict_id_feature_pddf = pd.read_pickle(file_to_load)
print("length of movie_id v.s. movie_property {}".format(len(dict_id_feature_pddf)))
file_to_load = open("info/raw_embed_item_mapping.pickle", "rb")
raw_embed_item_mapping = pickle.load(file_to_load)
file_to_load = open("info/raw_embed_user_mapping.pickle", "rb")
raw_embed_user_mapping = pickle.load(file_to_load)
# 加载模型
user_embedding_model = load_model('info/user_embeddings.h5', custom_objects)
embed_dim = 32

sample_data_pddf = action_data_pddf[['action_value', 'user_id', 'item_id', 'timestamp']]
sample_data_pddf.sort_values('timestamp', inplace=True)

sample_data_pddf_click = sample_data_pddf[sample_data_pddf['action_value'] == 1]
user_click_record = {}
for reviewerID, hist in tqdm(sample_data_pddf_click.groupby('user_id')):
    current_user_time_list = {}
    pos_list = hist['item_id'].tolist()
    time_list = hist['timestamp'].tolist()
    for idx, t in enumerate(time_list):
        current_user_time_list[t] = pos_list[idx:]
    user_click_record[str(reviewerID)] = current_user_time_list

sample_data_pddf = sample_data_pddf.drop_duplicates()
sample_data_pddf = sample_data_pddf.reset_index(drop=True)


def user_id_feat(x, i):
    return x[i]


#     return pd.Series(f_dict)

def min_max_norm(raw_list):
    #     current_mean = np.mean(raw_list)
    min_max_norm = [((float)(i) - min(raw_list)) / (max(raw_list) - min(raw_list)) for i in raw_list]
    return min_max_norm


#     if math.isclose(current_mean,0) or math.isclose(mean_value,0):
#         return raw_list
#     else:
#         raw_list = current_meanfloat(mean_value) * raw_list
#         return raw_list

def user_embed_func(x, user_click_record=user_click_record, user_embedding_model=user_embedding_model,
                    dict_item_mapping=raw_embed_item_mapping, dict_user_mapping=raw_embed_user_mapping):
    current_time_stamp = x['timestamp']
    if str(x['user_id']) in user_click_record.keys() and str(x['user_id']) in dict_user_mapping:
        current_click_record = user_click_record[str(x['user_id'])]
        #         last_ts = list(current_click_record.keys())[0]
        #         print("current stamp is {}".format(current_time_stamp))
        input_item_list = []
        for ts in current_click_record.keys():
            if current_time_stamp < ts:
                #                 print("found last ts {}".format(ts))
                input_item_list = current_click_record[ts]
                break
        # get embedding value
        user_id = x['user_id']
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
        # 做归一化
        return min_max_norm(updated_user_embs[0])
    else:
        #         print("zero click!!")
        return [0] * embed_dim


dict_id_feature_pddf['programId'] = dict_id_feature_pddf['programId'].astype(int)

sample_data_pddf = pd.merge(left=sample_data_pddf, right=dict_id_feature_pddf.drop_duplicates(), how='left',
                            left_on='item_id', right_on='programId')

# user id feature - user embedding
print("根据user_id的历史记录生成userid_feat（嵌入）")
# sample_data_pddf['userid_feat'] = sample_data_pddf.progress_apply(user_embed_func, axis=1)
sample_data_pddf['userid_feat'] = sample_data_pddf.apply(user_embed_func, axis=1)

print("将{}维用户嵌入转化为不同的连续型feature".format(embed_dim))
for i in tqdm(range(embed_dim)):
    sample_data_pddf['user_feature_{}'.format(i)] = sample_data_pddf['userid_feat'].apply(lambda x: user_id_feat(x, i))

mk_data = sample_data_pddf
dense_feature_size = embed_dim
sparse_feature_size = 6
for i in range(dense_feature_size):
    if i < embed_dim:
        mk_data['I{}'.format(i + 1)] = mk_data['user_feature_{}'.format(i)]

mk_sparse_features = ['C' + str(i) for i in range(1, sparse_feature_size + 1)]
mk_dense_features = ['I' + str(i) for i in range(1, dense_feature_size + 1)]
mk_data[mk_sparse_features] = mk_data[mk_sparse_features].fillna('-1', )
mk_data[mk_dense_features] = mk_data[mk_dense_features].fillna(0, )

mk_train, mk_test = train_test_split(mk_data, test_size=0.2)

continous_features = range(1, dense_feature_size + 1)
categorial_features = range(1, sparse_feature_size + 1)

output_dir = './'
with open(output_dir + 'tr.libsvm', 'w') as out_train:
    with open(output_dir + 'va.libsvm', 'w') as out_valid:
        for row in mk_train.iterrows():
            item_row = row[1]

            feat_vals = []
            for i in range(0, len(continous_features)):
                feat_vals.append(
                    str(continous_features[i]) + ':' + "{0:.6f}".format(item_row[mk_dense_features[i]]))

            for i in range(0, len(categorial_features)):
                #                 val = dicts.gen(i, features[mk_sparse_features[i]]) + categorial_feature_offset[i]
                feat_vals.append(str(item_row[mk_sparse_features[i]]) + ':1')

            label = item_row['action_value']
            if random.randint(0, 9999) % 10 != 0:
                out_train.write("{0} {1}\n".format(label, ' '.join(feat_vals)))
            else:
                out_valid.write("{0} {1}\n".format(label, ' '.join(feat_vals)))

with open(output_dir + 'te.libsvm', 'w') as out_test:
    for row in mk_test.iterrows():
        item_row = row[1]

        feat_vals = []
        for i in range(0, len(continous_features)):
            feat_vals.append(
                str(continous_features[i]) + ':' + "{0:.6f}".format(item_row[mk_dense_features[i]]))

        for i in range(0, len(categorial_features)):
            #                 val = dicts.gen(i, features[mk_sparse_features[i]]) + categorial_feature_offset[i]
            feat_vals.append(str(item_row[mk_sparse_features[i]]) + ':1')

        label = item_row['action_value']
        out_test.write("{0} {1}\n".format(label, ' '.join(feat_vals)))

# tar = tarfile.open("model.tar.gz", "w:gz")
# tar.add(model_name)
# tar.close()
# write_to_s3("model.tar.gz", bucket, "{}/model/rank/action/deepfm/latest/model.tar.gz".format(prefix))

# write_str_to_s3(json.dumps({
#     "loss": loss,
#     "auc": auc
# }),
#     bucket,
#     "{}/model/rank/action/deepfm/latest/metrics.json".format(prefix)
# )

run_script('/code/deepfm_model.sh')

# recommender-system-film-mk/1/model/rank/action/deepfm/latest/deepfm_model.tar.gz
model_file_name = "/code/deepfm_model.tar.gz"
model_key = '{}/model/rank/action/deepfm/latest/deepfm_model.tar.gz'.format(prefix)
write_to_s3(model_file_name, bucket, model_key)
