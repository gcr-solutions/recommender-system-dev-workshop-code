# %%writefile preprocessing.py

import argparse
import logging
import os.path
import pickle
import re

import boto3
import numpy as np
import pandas as pd

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)


def write_to_s3(filename, bucket, key):
    print("upload s3://{}/{}".format(bucket, key))
    with open(filename, 'rb') as f:  # Read in binary mode
        # return s3client.upload_fileobj(f, bucket, key)
        return s3.put_object(
            ACL='bucket-owner-full-control',
            Bucket=bucket,
            Key=key,
            Body=f
        )


def write_str_to_s3(content, bucket, key):
    print("write s3://{}/{}, content={}".format(bucket, key, content))
    s3.put_object(Body=str(content).encode("utf8"), Bucket=bucket, Key=key, ACL='bucket-owner-full-control')


def download_from_s3(filename, bucket, key):
    print("download_from_s3 s3://{}/{} to {}".format(bucket, key, filename))
    with open(filename, 'wb') as f:
        return s3.download_fileobj(bucket, key, f)


def list_s3_by_prefix_v2(s3_path, filter_func=None):
    bucket, key_prefix = get_bucket_key_from_s3_path(s3_path)
    return list_s3_by_prefix(bucket, key_prefix, filter_func)


def list_s3_by_prefix(bucket, key_prefix, filter_func=None):
    next_token = ''
    all_keys = []
    while True:
        if next_token:
            res = s3.list_objects_v2(
                Bucket=bucket,
                ContinuationToken=next_token,
                Prefix=key_prefix)
        else:
            res = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=key_prefix)

        if 'Contents' not in res:
            break

        if res['IsTruncated']:
            next_token = res['NextContinuationToken']
        else:
            next_token = ''

        if filter_func:
            keys = ["s3://{}/{}".format(bucket, item['Key']) for item in res['Contents'] if filter_func(item['Key'])]
        else:
            keys = ["s3://{}/{}".format(bucket, item['Key']) for item in res['Contents']]

        all_keys.extend(keys)

        if not next_token:
            break
    print("find {} files in s3://{}/{}".format(len(all_keys), bucket, key_prefix))
    return all_keys


def get_bucket_key_from_s3_path(s3_path):
    m = re.match(r"s3://(.*?)/(.*)", s3_path)
    return m.group(1), m.group(2)


def prepare_df(item_s3_path):
    return pd.read_csv(item_s3_path, sep="_!_", names=[
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


def gen_pickle_files(item_file_path, out_s3_path):
    logging.info(f"gen_pick_files(), "
                 f"\nitem_file_path={item_file_path}, "
                 f"\nout_s3_path={out_s3_path}")

    df = prepare_df(item_file_path)

    dicts_1 = gen_movie_id_movie_property_dict(df)
    dicts_2 = gen_movie_properties_to_movie_ids_dict(df)
    dicts_all = dicts_1
    dicts_all.update(dicts_2)
    bucket, out_prefix = get_bucket_key_from_s3_path(out_s3_path)
    for dict_name, dict_val in dicts_all.items():
        file_name = f'{dict_name}.pickle'
        # print("pickle =>", file_name)
        out_file = open(file_name, 'wb')
        pickle.dump(dict_val, out_file)
        out_file.close()
        # s3_url = S3Uploader.upload(file_name, out_s3_path)
        s3_url = write_to_s3(file_name, bucket, f'{out_prefix}/{file_name}')
        logging.info("write {}".format(s3_url))
    logging.info(f"generated {len(dicts_all)} pickle files")


def gen_movie_id_movie_property_dict(df):
    movie_id_movie_property_dict = {}
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
        movie_id_movie_property_dict[program_id] = program_dict

    result_dict = {
        'movie_id_movie_property_dict': movie_id_movie_property_dict
    }
    return result_dict


def convert_to_num(x):
    if x:
        try:
            return float(x)
        except Exception as e:
            return 0
    return 0


def sort_by_score(df):
    logging.info("sort_by_score() enter, df.columns: {}".format(df.columns))
    df['popularity'].fillna(0, inplace=True)
    df['ticket_num'].fillna(0, inplace=True)
    df['score'].fillna(0, inplace=True)

    df['popularity_log'] = np.log1p(df['popularity'].map(convert_to_num))
    df['ticket_num_log'] = np.log1p(df['ticket_num'].map(convert_to_num))
    df['score'] = df['score'].map(convert_to_num)

    popularity_log_max = df['popularity_log'].max()
    popularity_log_min = df['popularity_log'].min()
    ticket_num_log_max = df['ticket_num_log'].max()
    ticket_num_log_min = df['ticket_num_log'].min()

    df = df.drop(['popularity', 'ticket_num'], axis=1)

    score_max = df['score'].max()
    score_min = df['score'].min()
    df['popularity_scaled'] = ((df['popularity_log'] - popularity_log_min) / (
            popularity_log_max - popularity_log_min)) * 10
    df['ticket_num_scaled'] = (df['ticket_num_log'] - ticket_num_log_min) / (
            ticket_num_log_max - ticket_num_log_min) * 10
    df['score_scaled'] = ((df['score'] - score_min) / (score_max - score_min)) * 10

    df['cal_score'] = df['popularity_scaled'] + df['ticket_num_scaled'] + df['score_scaled']

    df_with_score = df.drop(
        ['score', 'popularity_scaled', 'ticket_num_scaled', 'score_scaled'], axis=1)
    df_sorted = df_with_score.sort_values(by='cal_score', ascending=False)

    logging.info("sort_by_score() return, df.columns: {}".format(df_sorted.columns))
    return df_sorted


def gen_movie_properties_to_movie_ids_dict(df):
    df_sorted = sort_by_score(df)

    movie_director_movie_ids_dict = {}
    movie_language_movie_ids_dict = {}
    movie_level_movie_ids_dict = {}
    movie_year_movie_ids_dict = {}

    movie_category_movie_ids_dict = {}
    movie_actor_movie_ids_dict = {}

    for row in df_sorted.iterrows():
        item_row = row[1]
        # program_id = {"id": item_row['program_id'], "score": item_row['cal_score'] }
        program_id = item_row['program_id']
        for key in [item for item in get_single_item(item_row['director']) if item is not None]:
            movie_director_movie_ids_dict.setdefault(key, []).append(program_id)

        for key in [item for item in get_single_item(item_row['level']) if item is not None]:
            movie_level_movie_ids_dict.setdefault(key, []).append(program_id)

        for key in [item for item in get_single_item(item_row['release_year']) if item is not None]:
            movie_year_movie_ids_dict.setdefault(key, []).append(program_id)

        for key in [item for item in get_single_item(item_row['language']) if item is not None]:
            movie_language_movie_ids_dict.setdefault(key, []).append(program_id)

        for key in [item for item in get_category(item_row['category_property']) if item is not None]:
            movie_category_movie_ids_dict.setdefault(key, []).append(program_id)

        for key in [item for item in get_actor(item_row['actor']) if item is not None]:
            movie_actor_movie_ids_dict.setdefault(key, []).append(program_id)

    result_dict = {
        'movie_director_movie_ids_dict': movie_director_movie_ids_dict,
        'movie_language_movie_ids_dict': movie_language_movie_ids_dict,
        'movie_level_movie_ids_dict': movie_level_movie_ids_dict,
        'movie_year_movie_ids_dict': movie_year_movie_ids_dict,
        'movie_category_movie_ids_dict': movie_category_movie_ids_dict,
        'movie_actor_movie_ids_dict': movie_actor_movie_ids_dict
    }

    return result_dict


def get_actor(actor_str):
    if not actor_str or str(actor_str).lower() in ['nan', 'nr', '', "''", '""']:
        return [None]
    actor_arr = actor_str.split('|')
    return [item.strip().lower() for item in actor_arr
            if len(item.strip()) > 0 and item.strip() not in ("''", '""')]


def get_category(category_property):
    if not category_property or str(category_property).lower() in ['nan', 'nr', '', "''", '""']:
        return [None]
    if not category_property:
        return [None]
    return [item.strip().lower() for item in category_property.split('|')
            if len(item.strip()) > 0 and item.strip() not in ("''", '""')]


def get_single_item(item):
    if not item or str(item).lower().strip() in ['nan', 'nr', '', "''", '""']:
        return [None]
    return [str(item).lower().strip()]


if __name__ == '__main__':
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

    item_s3_key = f"{prefix}/system/item-data/item.csv"
    out_s3_path = f"s3://{bucket}/{prefix}/feature/content/inverted-list"
    if not os.path.exists("./info"):
        os.makedirs("./info")

    download_from_s3("./info/item.csv", bucket, item_s3_key)
    gen_pickle_files("./info/item.csv", out_s3_path)
