from __future__ import print_function
import boto3
import os
import kg
# from tqdm import tqdm
import argparse
import json
import dglke

# tqdm.pandas()
# pandarallel.initialize(progress_bar=True)
# bucket = os.environ.get("BUCKET_NAME", " ")
# raw_data_folder = os.environ.get("RAW_DATA", " ")
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# tqdm_notebook().pandas()
print("dglke version:", dglke.__version__)


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


region = None
param_path = os.path.join('/opt/ml/', 'input/config/hyperparameters.json')

if os.path.exists(param_path):
    print("load param from {}".format(param_path))
    with open(param_path) as f:
        hp = json.load(f)
        bucket = hp['bucket']
        prefix = hp['prefix']
        region = hp.get("region")
else:
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', type=str)
    parser.add_argument('--prefix', type=str)
    parser.add_argument("--region", type=str, help="aws region")
    args, _ = parser.parse_known_args()
    bucket = args.bucket
    prefix = args.prefix
    if args.region:
        region = args.region

if region:
    print("region:", region)
    boto3.setup_default_session(region_name=region)

if prefix.endswith("/"):
    prefix = prefix[:-1]

print("bucket={}".format(bucket))
print("prefix='{}'".format(prefix))

s3client = boto3.client('s3')

out_s3_path = "s3://{}/{}/feature/content/inverted-list".format(bucket, prefix)

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)

# prepare model for batch process
meta_file_prefix = "{}/model/meta_files".format(prefix)
os.environ['GRAPH_BUCKET'] = bucket
os.environ['KG_DBPEDIA_KEY'] = '{}/kg_dbpedia.txt'.format(meta_file_prefix)
os.environ['KG_ENTITY_KEY'] = '{}/entities_dbpedia.dict'.format(
    meta_file_prefix)
os.environ['KG_RELATION_KEY'] = '{}/relations_dbpedia.dict'.format(
    meta_file_prefix)
os.environ['KG_DBPEDIA_TRAIN_KEY'] = '{}/kg_dbpedia.txt'.format(
    meta_file_prefix)
os.environ['KG_ENTITY_TRAIN_KEY'] = '{}/entities_dbpedia.dict'.format(
    meta_file_prefix)
os.environ['KG_RELATION_TRAIN_KEY'] = '{}/relations_dbpedia.dict'.format(
    meta_file_prefix)
os.environ['KG_ENTITY_INDUSTRY_KEY'] = '{}/entity_industry.txt'.format(
    meta_file_prefix)
os.environ['KG_VOCAB_KEY'] = '{}/vocab.json'.format(meta_file_prefix)
os.environ['DATA_INPUT_KEY'] = ''
os.environ['TRAIN_OUTPUT_KEY'] = '{}/model/rank/content/dkn_embedding_latest/'.format(
    prefix)

kg_path = os.environ['GRAPH_BUCKET']
dbpedia_key = os.environ['KG_DBPEDIA_KEY']
entity_key = os.environ['KG_ENTITY_KEY']
relation_key = os.environ['KG_RELATION_KEY']
dbpedia_train_key = os.environ['KG_DBPEDIA_TRAIN_KEY']
entity_train_key = os.environ['KG_ENTITY_TRAIN_KEY']
relation_train_key = os.environ['KG_RELATION_TRAIN_KEY']
entity_industry_key = os.environ['KG_ENTITY_INDUSTRY_KEY']
vocab_key = os.environ['KG_VOCAB_KEY']
data_input_key = os.environ['DATA_INPUT_KEY']
train_output_key = os.environ['TRAIN_OUTPUT_KEY']

env = {
    'GRAPH_BUCKET': kg_path,
    'KG_DBPEDIA_KEY': dbpedia_key,
    'KG_ENTITY_KEY': entity_key,
    'KG_RELATION_KEY': relation_key,
    'KG_DBPEDIA_TRAIN_KEY': dbpedia_train_key,
    'KG_ENTITY_TRAIN_KEY': entity_train_key,
    'KG_RELATION_TRAIN_KEY': relation_train_key,
    'KG_ENTITY_INDUSTRY_KEY': entity_industry_key,
    'KG_VOCAB_KEY': vocab_key,
    'DATA_INPUT_KEY': data_input_key,
    'TRAIN_OUTPUT_KEY': train_output_key
}

print("Kg env: {}".format(env))
graph = kg.Kg(env, region=region)  # Where we keep the model when it's loaded
# model = encoding.encoding(graph, env)
graph.train()
# graph.train(max_step=2000)
