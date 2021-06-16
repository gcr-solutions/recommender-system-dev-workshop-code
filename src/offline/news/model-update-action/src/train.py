from __future__ import print_function

# from tqdm import tqdm
import argparse
import glob
import json
import os
import shutil
import subprocess

import boto3

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


def run_script(script):
    print("run_script: '{}'".format(script))
    re_code, out_msg = subprocess.getstatusoutput([script])
    print("run_script re_code:", re_code)
    for line in out_msg.split("\n"):
        print(line)
    if re_code != 0:
        raise Exception(out_msg)


param_path = os.path.join('/opt/ml/', 'input/config/hyperparameters.json')
parser = argparse.ArgumentParser()
model_dir = None
training_dir = None
validation_dir = None

if os.path.exists(param_path):
    # running training job

    print("load param from {}".format(param_path))
    with open(param_path) as f:
        hp = json.load(f)
        print("hyperparameters:", hp)
        bucket = hp['bucket']
        prefix = hp['prefix']
    # parser.add_argument('--bucket', type=str)
    # parser.add_argument('--prefix', type=str)
    parser.add_argument('--model_dir', type=str,
                        default=os.environ.get('SM_MODEL_DIR', '/opt/ml/model'))
    parser.add_argument('--training_dir', type=str,
                        default=os.environ.get('SM_CHANNEL_TRAINING', '/opt/ml/input/data/training'))
    parser.add_argument('--validation_dir', type=str,
                        default=os.environ.get('SM_CHANNEL_VALIDATION', '/opt/ml/input/data/validation'))
    args, _ = parser.parse_known_args()
    # bucket = args.bucket
    # prefix = args.prefix
    model_dir = args.model_dir
    training_dir = args.training_dir
    validation_dir = args.validation_dir
    print("model_dir: {}".format(model_dir))
    print("training_dir: {}".format(training_dir))
    print("validation_dir: {}".format(validation_dir))

    print(f"files in {training_dir}:", glob.glob(
        os.path.join(training_dir, '*')))
    print(f"files in {validation_dir}:", glob.glob(
        os.path.join(validation_dir, '*')))

else:
    # running processing job
    parser.add_argument('--bucket', type=str)
    parser.add_argument('--prefix', type=str)
    args, _ = parser.parse_known_args()
    bucket = args.bucket
    prefix = args.prefix

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

model_s3_key = "{}/model/rank/action/dkn/latest/model.tar.gz".format(prefix)
# os.chdir("/opt/ml/code/")

train_file_name = 'action_train.csv'
val_file_name = 'action_val.csv'
train_local_folder = 'model-update-dkn/train/'
val_local_folder = 'model-update-dkn/val/'

for local_folder in [train_local_folder, val_local_folder, 'info']:
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)

# dkn模型文件下载
local_folder = "info"
file_name_list = ['dkn_entity_embedding.npy',
                  'dkn_context_embedding.npy', 'dkn_word_embedding.npy']
s3_folder = '{}/model/rank/content/dkn_embedding_latest/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
shutil.move("info/dkn_entity_embedding.npy",
            "model-update-dkn/train/entity_embeddings_TransE_128.npy")
shutil.move("info/dkn_context_embedding.npy",
            "model-update-dkn/train/context_embeddings_TransE_128.npy")
shutil.move("info/dkn_word_embedding.npy",
            "model-update-dkn/train/word_embeddings_300.npy")

train_file_local = os.path.join(training_dir, train_file_name)
val_file_local = os.path.join(validation_dir, val_file_name)

if os.path.exists(train_file_local) and os.path.exists(val_file_local):
    print("copy training/val files to ./model-update-dkn/")
    shutil.move(train_file_local, train_local_folder)
    shutil.move(val_file_local, val_local_folder)
else:
    file_name_list = [train_file_name]
    s3_folder = '{}/system/action-data/'.format(prefix)
    sync_s3(file_name_list, s3_folder, train_local_folder)
    file_name_list = [val_file_name]
    s3_folder = '{}/system/action-data/'.format(prefix)
    sync_s3(file_name_list, s3_folder, val_local_folder)

cwd_path = os.getcwd()
print("cwd_path:", cwd_path)
run_script("./embed_dkn_wrapper.sh")
model_file = "./model-update-dkn/model_latest/model.tar.gz"

if not os.path.exists(model_file):
    raise Exception("Cannot find file model.tar.gz")

write_to_s3(model_file, bucket, model_s3_key)

if model_dir:
    print("copy file {} to {}".format(model_file, model_dir))
    shutil.copyfile(model_file, os.path.join(model_dir, "model.tar.gz"))
