import argparse
import logging
import os
import pickle
import json
import time
import re
import argparse
import boto3
import pandas as pd
from sklearn.preprocessing import LabelEncoder


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
parser.add_argument("--region", type=str, help="aws region")
parser.add_argument("--method", type=str)
args, _ = parser.parse_known_args()
print("args:", args)

if args.region:
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix
method = args.method

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

s3client = boto3.client('s3')
personalize = boto3.client('personalize', args.region)
sts = boto3.client('sts')

get_caller_identity_response = sts.get_caller_identity()
aws_account_id = get_caller_identity_response["Account"]
print("aws_account_id:{}".format(aws_account_id))

out_s3_path = "s3://{}/{}/feature/content/inverted-list".format(bucket, prefix)

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)

file_name_list = ['item.csv']
s3_folder = '{}/system/item-data'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

#创建ItemDatasetImportJob
ps_item_file_name_list = ['ps_item.csv']
ps_item_s3_folder = '{}/system/ps-ingest-data/item'.format(prefix)
sync_s3(ps_item_file_name_list, ps_item_s3_folder, local_folder)

ps_config_file_name = ['ps_config.json']
ps_config_s3_folder = '{}/system/ps-config'.format(prefix)
sync_s3(ps_config_file_name, ps_config_s3_folder, local_folder)

def add_item_batch():
    lbe = LabelEncoder()
    df_filter_item = pd.read_csv('info/item.csv', sep='_!_', names=[
        'news_id', 'type_code', 'type', 'title', 'keywords', 'popularity', 'new'])

    df_filter_item['encode_id'] = lbe.fit_transform(df_filter_item['news_id'])

    raw_item_id_list = list(map(str, df_filter_item['news_id'].values))
    code_item_id_list = list(map(int, df_filter_item['encode_id'].values))
    raw_embed_item_id_dict = dict(zip(raw_item_id_list, code_item_id_list))
    embed_raw_item_id_dict = dict(zip(code_item_id_list, raw_item_id_list))

    file_name = 'info/raw_embed_item_mapping.pickle'
    output_file = open(file_name, 'wb')
    pickle.dump(raw_embed_item_id_dict, output_file)
    output_file.close()
    write_to_s3(file_name, bucket,
                "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))

    file_name = 'info/embed_raw_item_mapping.pickle'
    output_file = open(file_name, 'wb')
    pickle.dump(embed_raw_item_id_dict, output_file)
    output_file.close()
    write_to_s3(file_name, bucket,
                "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))


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

def create_item_dataset_import_job():
    ps_config = get_ps_config_from_s3()
    dataset_group_arn = get_dataset_group_arn(ps_config['DatasetGroupName'])
    dataset_arn = get_dataset_arn(dataset_group_arn, ps_config['ItemDatasetName'])
    response = personalize.create_dataset_import_job(
        jobName="item-dataset-import-job-{}".format(int(time.time())),
        datasetArn=dataset_arn,
        dataSource={
            'dataLocation': "s3://{}/{}/system/ps-ingest-data/item/ps_item.csv".format(bucket, prefix)
        },
        roleArn="arn:aws:iam::{}:role/gcr-rs-personalize-role".format(aws_account_id)
    )

    item_dataset_import_job_arn = response['datasetImportJobArn']
    print("item_dataset_import_job_arn:{}".format(item_dataset_import_job_arn))

    # check status
    max_time = time.time() + 3 * 60 * 60
    while time.time() < max_time:
        describe_dataset_import_job_response = personalize.describe_dataset_import_job(
            datasetImportJobArn=item_dataset_import_job_arn
        )
        status = describe_dataset_import_job_response["datasetImportJob"]['status']
        print("DatasetImportJob: {}".format(status))

        if status == "ACTIVE":
            print("ItemDatasetImportJob Create Successfully!")
            break
        elif status == "CREATE FAILED":
            print("ItemDatasetImportJob Create failed!")
            break
        else:
            time.sleep(60)

    print("ItemDatasetImportJob Exceed Max Create Time!")



add_item_batch()
if method != "customize":
    create_item_dataset_import_job()



