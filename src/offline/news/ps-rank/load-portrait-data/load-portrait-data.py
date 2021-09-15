import argparse
import json
import os
import boto3
import time

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


def write_buffer_to_table(batch_arr, db_table):
    with db_table.batch_writer() as batch:
        for item in batch_arr:
            batch.put_item(
                Item={
                    'user_id': str(item[0]),
                    'data': json.dumps(item[1], ensure_ascii=False),
                    'update_at': int(time.time())
                }
            )


def get_stage(bucket, region):
    # aws-gcr-rs-sol-dev-ap-southeast-1-522244679887-portrait
    if '-dev-workshop-' in bucket:
        return 'dev-workshop'
    if '-demo-' in bucket:
        return 'demo'
    if '-dev-' in bucket:
        return 'dev'
    stage = str(bucket).replace('aws-gcr-rs-sol-', '').replace("-{}".format(str(region)), '#').split("#")[0]
    return stage


parser = argparse.ArgumentParser()
parser.add_argument('--bucket', type=str)
parser.add_argument('--prefix', type=str)
parser.add_argument("--region", type=str, help="aws region")
args, _ = parser.parse_known_args()
print("args:", args)

aws_region = args.region
print("region:", aws_region)
boto3.setup_default_session(region_name=aws_region)
dynamodb = boto3.resource('dynamodb', region_name=aws_region)

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

file_name_list = ['portrait.jsonl']
s3_folder = '{}/feature/recommend-list/portrait'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
local_file = "info/{}".format(file_name_list[0])

# aws-gcr-rs-sol-dev-ap-southeast-1-522244679887-portrait
stage = get_stage(bucket, aws_region)

table_name = "rs-news-ps-rank-{}-portrait".format(stage)
table = dynamodb.Table(table_name)

item_count = 0
buffer = []

with open(local_file, "r") as input:
    while True:
        json_line = input.readline()
        if not json_line:
            break

        item_count = item_count + 1
        if item_count % 1000 == 0:
            print("write item to dynamodb table {} - {}".format(table_name, item_count))

        buffer.append(json.loads(json_line))

        if len(buffer) >= 500:
            write_buffer_to_table(buffer, table)
            buffer.clear()

if len(buffer) > 0:
    write_buffer_to_table(buffer, table)

print("write {} items to {}".format(item_count, table_name))
