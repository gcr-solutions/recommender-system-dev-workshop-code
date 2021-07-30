# rank batch logic
import pickle
import argparse
import boto3
import os
import itertools
import tarfile
import pandas as pd
from tqdm import tqdm
import glob
from sklearn.model_selection import train_test_split
from tensorflow.contrib import predictor


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

def find_model_path(model_extract_dir):
    for name in glob.glob(os.path.join(model_extract_dir, '**', 'saved_model.pb'), recursive=True):
        print("found model saved_model.pb in {} !".format(name))
        model_path = '/'.join(name.split('/')[0:-1])
        print("model_path:{}".format(model_path))
        return model_path


local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)

# recall batch 结果记载
file_name_list = ['recall_batch_result.pickle']
s3_folder = '{}/feature/recommend-list/movie'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 用户画像数据加载
file_name_list = ['portrait.pickle']
s3_folder = '{}/feature/recommend-list/portrait'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 倒排列表的pickle文件
file_name_list = ['movie_id_movie_feature_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# deepfm模型文件下载
file_name_list = ['deepfm_model.tar.gz']
s3_folder = '{}/model/rank/action/deepfm/latest/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# 加载pickle文件
file_to_load = open("info/recall_batch_result.pickle", "rb")
recall_batch_result = pickle.load(file_to_load)
file_to_load = open("info/portrait.pickle", "rb")
user_portrait = pickle.load(file_to_load)
file_to_load = open("info/movie_id_movie_feature_dict.pickle", "rb")
dict_id_feature_pddf = pd.read_pickle(file_to_load)
print("length of movie_id v.s. movie_property {}".format(len(dict_id_feature_pddf)))
# 解压缩deepfm模型
tar = tarfile.open("info/deepfm_model.tar.gz", "r")
file_names = tar.getnames()
for file_name in file_names:
    tar.extract(file_name, "info/")
tar.close
# deepfm_model = predictor.from_saved_model('./info/serve/1616411804')

model_path = find_model_path('./info/serve/')
deepfm_model = predictor.from_saved_model(model_path)

# 加载recall结果
file_to_load = open("info/recall_batch_result.pickle", "rb")
dict_recall_result = pickle.load(file_to_load)
embed_dim = 32

# 整理recall结果
data_input_pddf_dict = {}
data_input_pddf_dict['userId'] = []
data_input_pddf_dict['programId'] = []
for user_k, result_v in dict_recall_result.items():
    for item_v in result_v.keys():
        data_input_pddf_dict['userId'].append(str(user_k))
        data_input_pddf_dict['programId'].append(str(item_v))
data_input_pddf = pd.DataFrame.from_dict(data_input_pddf_dict)

data_input_pddf['programId'] = data_input_pddf['programId'].astype(int)

dict_id_feature_pddf['programId'] = dict_id_feature_pddf['programId'].astype(int)

data_input_pddf = pd.merge(left=data_input_pddf, right=dict_id_feature_pddf.drop_duplicates(), how='left',
                           left_on='programId', right_on='programId')


def user_embed(x, user_portrait):
    if x in user_portrait.keys():
        #         print(user_portrait[x])
        return user_portrait[x]['ub_embeddding'][0]
    else:
        return [0] * 32


def user_id_feat(x, i):
    return float(x[i])


# user id feature - user embedding
data_input_pddf['userid_feat'] = data_input_pddf['userId'].apply(lambda x: user_embed(x, user_portrait))
for i in range(32):
    data_input_pddf['user_feature_{}'.format(i)] = data_input_pddf['userid_feat'].apply(lambda x: user_id_feat(x, i))

mk_test_data = data_input_pddf
dense_feature_size = embed_dim
sparse_feature_size = 6
for i in range(dense_feature_size):
    if i < embed_dim:
        mk_test_data['I{}'.format(i + 1)] = mk_test_data['user_feature_{}'.format(i)]
        mk_test_data.drop(['user_feature_{}'.format(i)], axis=1)

mk_test_data.drop(['userid_feat'], axis=1)
mk_sparse_features = ['C' + str(i) for i in range(1, sparse_feature_size + 1)]
mk_dense_features = ['I' + str(i) for i in range(1, dense_feature_size + 1)]
mk_test_data[mk_sparse_features] = mk_test_data[mk_sparse_features].fillna('-1', )
mk_test_data[mk_dense_features] = mk_test_data[mk_dense_features].fillna(0, )

test_example = {}
test_example['feat_ids'] = []
test_example['feat_vals'] = []
for row in mk_test_data.iterrows():
    row_content = row[1]
    feat_ids = []
    feat_vals = []
    for i, v in enumerate(mk_dense_features):
        feat_ids.append(i + 1)
        feat_vals.append(row_content[v])
    for i, v in enumerate(mk_sparse_features):
        feat_ids.append(row_content[v])
        feat_vals.append(1)
    test_example['feat_ids'].append(feat_ids)
    test_example['feat_vals'].append(feat_vals)

result = deepfm_model(test_example)

mk_test_data['rank_score'] = [v for v in list(result['prob'])]

rank_result = {}
for reviewerID, hist in tqdm(mk_test_data.groupby('userId')):
    candidate_list = hist['programId'].tolist()
    score_list = hist['rank_score'].tolist()
    id_score_dict = dict(zip(candidate_list, score_list))
    sort_id_score_dict = {k: v for k, v in sorted(id_score_dict.items(), key=lambda item: item[1], reverse=True)}
    rank_result[reviewerID] = sort_id_score_dict

file_name = 'info/rank_batch_result.pickle'
output_file = open(file_name, 'wb')
pickle.dump(rank_result, output_file)
output_file.close()

write_to_s3(file_name,
            bucket,
            '{}/feature/recommend-list/movie/rank_batch_result.pickle'.format(prefix))
