import argparse
import json
import logging
import os
import pickle
import time
import re

import boto3
import pandas as pd
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)


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


def prepare_df(item_path):
    return pd.read_csv(item_path, sep="_!_", names=[
        "program_id",
        "program_type",
        "program_name",
        "release_year",
        "director",
        "actor",
        "category_property",
        "language",
        "ticket_num",
        "popularity",
        "score",
        "level",
        "is_new"])


def get_actor(actor_str):
    if not actor_str or str(actor_str).lower() in ['nan', 'nr', '']:
        return [None]
    actor_arr = actor_str.split('|')
    return [item.strip().lower() for item in actor_arr]


def get_category(category_property):
    if not category_property or str(category_property).lower() in ['nan', 'nr', '']:
        return [None]
    if not category_property:
        return [None]
    return [item.strip().lower() for item in category_property.split('|')]


def get_single_item(item):
    if not item or str(item).lower().strip() in ['nan', 'nr', '']:
        return [None]
    return [str(item).lower().strip()]


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
region = args.region
method = args.method

print(f"bucket:{bucket}, prefix:{prefix}")
print("region={}".format(region))
print("method={}".format(method))

s3 = boto3.client('s3')
s3client = s3
personalize = boto3.client('personalize', args.region)
sts = boto3.client('sts')

get_caller_identity_response = sts.get_caller_identity()
aws_account_id = get_caller_identity_response["Account"]
print("aws_account_id:{}".format(aws_account_id))


local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)

# 行为数据加载
file_name_list = ['user.csv']
s3_folder = '{}/system/user-data/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

#创建UserDatasetImportJob
ps_user_file_name_list = ['ps_user.csv']
ps_user_s3_folder = '{}/system/ps-ingest-data/user'.format(prefix)
sync_s3(ps_user_file_name_list, ps_user_s3_folder, local_folder)

ps_config_file_name = ['ps_config.json']
ps_config_s3_folder = '{}/system/ps-config'.format(prefix)
sync_s3(ps_config_file_name, ps_config_s3_folder, local_folder)

# !!!应该用用户注册数据来生成encoding map
user_df = pd.read_csv('info/user.csv', sep='_!_',
                      names=['user_id', 'sex', 'age', 'timestamp', 'name'])

lbe = LabelEncoder()

user_df['encode_id'] = lbe.fit_transform(user_df['user_id'])

# constructu mapping dictionary
raw_user_id_list = list(map(str, user_df['user_id'].values))
code_user_id_list = list(map(int, user_df['encode_id'].values))
raw_embed_user_id_dict = dict(zip(raw_user_id_list, code_user_id_list))
embed_raw_user_id_dict = dict(zip(code_user_id_list, raw_user_id_list))

file_name = 'info/raw_embed_user_mapping.pickle'
output_file = open(file_name, 'wb')
pickle.dump(raw_embed_user_id_dict, output_file)
output_file.close()
write_to_s3(file_name, bucket, "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))

file_name = 'info/embed_raw_user_mapping.pickle'
output_file = open(file_name, 'wb')
pickle.dump(embed_raw_user_id_dict, output_file)
output_file.close()
write_to_s3(file_name, bucket, "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))


def get_ps_config_from_s3():
    infile = open('info/ps_config.json')
    ps_config = json.load(infile)
    infile.close()
    return ps_config

def get_dataset_group_arn(dataset_group_name):
    response = personalize.list_dataset_groups()
    for dataset_group in response["datasetGroups"]:
        if dataset_group["name"] == dataset_group_name:
            return dataset_group["datasetGroupArn"]

def get_dataset_arn(dataset_group_arn, dataset_name):
    response = personalize.list_datasets(
        datasetGroupArn=dataset_group_arn
    )
    for dataset in response["datasets"]:
        if dataset["name"] == dataset_name:
            return dataset["datasetArn"]

def create_user_dataset_import_job():
    ps_config = get_ps_config_from_s3()
    dataset_group_arn = get_dataset_group_arn(ps_config['DatasetGroupName'])
    dataset_arn = get_dataset_arn(dataset_group_arn, ps_config['UserDatasetName'])
    response = personalize.create_dataset_import_job(
        jobName="user-dataset-import-job-{}".format(int(time.time())),
        datasetArn=dataset_arn,
        dataSource={
            'dataLocation': "s3://{}/{}/system/ps-ingest-data/user/ps_user.csv".format(bucket, prefix)
        },
        roleArn="arn:aws:iam::{}:role/gcr-rs-personalize-role-{}".format(aws_account_id,region)
    )

    user_dataset_import_job_arn = response['datasetImportJobArn']
    print("user_dataset_import_job_arn:{}".format(user_dataset_import_job_arn))

    # check status
    max_time = time.time() + 3 * 60 * 60
    while time.time() < max_time:
        describe_dataset_import_job_response = personalize.describe_dataset_import_job(
            datasetImportJobArn=user_dataset_import_job_arn
        )
        status = describe_dataset_import_job_response["datasetImportJob"]['status']
        print("DatasetImportJob: {}".format(status))

        if status == "ACTIVE":
            print("UserDatasetImportJob Create Successfully!")
            break
        elif status == "CREATE FAILED":
            print("UserDatasetImportJob Create failed!")
            break
        else:
            time.sleep(60)

    print("UserDatasetImportJob Exceed Max Create Time!")


if "ps" in method:
    create_user_dataset_import_job()



