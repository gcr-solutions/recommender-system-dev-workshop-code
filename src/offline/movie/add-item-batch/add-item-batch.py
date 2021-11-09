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
parser.add_argument("--method", type=str, default='customize', help="method name")

args, _ = parser.parse_known_args()
print("args:", args)

if args.region:
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix
method = args.method
region = args.region

if prefix.endswith("/"):
    prefix = prefix[:-1]

print(f"bucket:{bucket}, prefix:{prefix}")
print("region={}".format(region))
print("method={}".format(method))

s3 = boto3.client('s3')
personalize = boto3.client('personalize', args.region)
s3client = s3
sts = boto3.client('sts')

get_caller_identity_response = sts.get_caller_identity()
aws_account_id = get_caller_identity_response["Account"]
print("aws_account_id:{}".format(aws_account_id))

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)


file_name_list = ['item.csv']
s3_folder = '{}/system/item-data/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

df = prepare_df("info/item.csv")

movie_id_movie_property_data = {}
row_cnt = 0
for row in df.iterrows():
    item_row = row[1]
    program_id = str(item_row['program_id'])
    program_dict = {
        'director': get_single_item(item_row['director']),
        'level': get_single_item(item_row['level']),
        'year': get_single_item(item_row['release_year']),
        'actor': get_actor(item_row['actor']),
        'category': get_category(item_row['category_property']),
        'language': get_single_item(item_row['language'])
    }
    row_content = []
    row_content.append(str(item_row['program_id']))
    row_content.append(program_dict['director'])
    row_content.append(program_dict['level'])
    row_content.append(program_dict['year'])
    row_content.append(program_dict['actor'])
    row_content.append(program_dict['category'])
    row_content.append(program_dict['language'])
    movie_id_movie_property_data['row_{}'.format(row_cnt)] = row_content
    row_cnt = row_cnt + 1

raw_data_pddf = pd.DataFrame.from_dict(movie_id_movie_property_data, orient='index',
                                       columns=['programId', 'director', 'level', 'year', 'actor', 'actegory',
                                                'language'])
raw_data_pddf = raw_data_pddf.reset_index(drop=True)
# raw_data_pddf.head()

sample_data_pddf = raw_data_pddf

# generate lable encoding/ sparse feature
lbe = LabelEncoder()
sample_data_pddf['encode_id'] = lbe.fit_transform(sample_data_pddf['programId'])

raw_item_id_list = list(map(str, sample_data_pddf['programId'].values))
code_item_id_list = list(map(int, sample_data_pddf['encode_id'].values))
raw_embed_item_id_dict = dict(zip(raw_item_id_list, code_item_id_list))
embed_raw_item_id_dict = dict(zip(code_item_id_list, raw_item_id_list))

file_name = 'info/raw_embed_item_mapping.pickle'
output_file = open(file_name, 'wb')
pickle.dump(raw_embed_item_id_dict, output_file)
output_file.close()
write_to_s3(file_name, bucket, "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))

file_name = 'info/embed_raw_item_mapping.pickle'
output_file = open(file_name, 'wb')
pickle.dump(embed_raw_item_id_dict, output_file)
output_file.close()
write_to_s3(file_name, bucket, "{}/feature/action/{}".format(prefix, file_name.split('/')[-1]))

#创建ItemDatasetImportJob
ps_item_file_name_list = ['ps_item.csv']
ps_item_s3_folder = '{}/system/ps-ingest-data/item'.format(prefix)
sync_s3(ps_item_file_name_list, ps_item_s3_folder, local_folder)

ps_config_file_name = ['ps_config.json']
ps_config_s3_folder = '{}/system/ps-config'.format(prefix)
sync_s3(ps_config_file_name, ps_config_s3_folder, local_folder)

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
        roleArn="arn:aws:iam::{}:role/gcr-rs-personalize-role-{}".format(aws_account_id, region)
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


if "ps" in method:
    create_item_dataset_import_job()