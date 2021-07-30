import argparse
import logging
import os
import pickle
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

print(f"bucket:{bucket}, prefix:{prefix}")

s3 = boto3.client('s3')
s3client = s3

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
