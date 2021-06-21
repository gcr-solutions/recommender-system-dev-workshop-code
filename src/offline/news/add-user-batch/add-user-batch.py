import argparse
import logging
import os
import pickle
import re
import argparse
import boto3
import pandas as pd
from sklearn.preprocessing import LabelEncoder

s3client = boto3.client('s3')

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)


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
args, _ = parser.parse_known_args()
bucket = args.bucket
prefix = args.prefix

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

out_s3_path = "s3://{}/{}/feature/content/inverted-list".format(bucket, prefix)

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
# 行为/物品数据同步
file_name_list = ['user.csv']
s3_folder = '{}/system/user-data'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)


def add_user_batch():
    lbe = LabelEncoder()
    df_filter_user = pd.read_csv('info/user.csv', sep='_!_',
                                 names=['user_id', 'gender', 'age', 'timestamp', 'user_name'])

    df_filter_user['encode_id'] = lbe.fit_transform(df_filter_user['user_id'])

    # constructu mapping dictionary
    raw_user_id_list = list(map(str, df_filter_user['user_id'].values))
    code_user_id_list = list(map(int, df_filter_user['encode_id'].values))
    raw_embed_user_id_dict = dict(zip(raw_user_id_list, code_user_id_list))
    embed_raw_user_id_dict = dict(zip(code_user_id_list, raw_user_id_list))

    file_name = 'info/raw_embed_user_mapping.pickle'
    output_file = open(file_name, 'wb')
    pickle.dump(raw_embed_user_id_dict, output_file)
    output_file.close()
    write_to_s3(file_name, bucket,
                "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))

    file_name = 'info/embed_raw_user_mapping.pickle'
    output_file = open(file_name, 'wb')
    pickle.dump(embed_raw_user_id_dict, output_file)
    output_file.close()
    write_to_s3(file_name, bucket,
                "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))


add_user_batch()
