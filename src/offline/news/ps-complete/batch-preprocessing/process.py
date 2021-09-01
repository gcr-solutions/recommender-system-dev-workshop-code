import argparse
import json
import os
import pickle

import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, size, row_number, expr, array_join, to_json, struct
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql.window import Window
from functools import partial


def list_s3_by_prefix(bucket, prefix, filter_func=None):
    print(f"list_s3_by_prefix bucket: {bucket}, prefix: {prefix}")
    s3_bucket = boto3.resource('s3').Bucket(bucket)
    if filter_func is None:
        key_list = [s.key for s in s3_bucket.objects.filter(Prefix=prefix)]
    else:
        key_list = [s.key for s in s3_bucket.objects.filter(
            Prefix=prefix) if filter_func(s.key)]

    print("list_s3_by_prefix return:", key_list)
    return key_list


def s3_copy(bucket, from_key, to_key):
    s3_bucket = boto3.resource('s3').Bucket(bucket)
    copy_source = {
        'Bucket': bucket,
        'Key': from_key
    }
    s3_bucket.copy(copy_source, to_key)
    print("copied s3://{}/{} to s3://{}/{}".format(bucket, from_key, bucket, to_key))


s3client = boto3.client('s3')
parser = argparse.ArgumentParser(description="app inputs and outputs")
parser.add_argument("--bucket", type=str, help="s3 bucket")
parser.add_argument("--prefix", type=str,
                    help="s3 input key prefix")

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

input_user_file = "s3://{}/{}/system/ingest-data/user/".format(bucket, prefix)
emr_ps_batch_output_key_prefix = "{}/system/emr/batch-preprocessing/output/ps-complete-batch".format(
    prefix)
emr_ps_batch_output_bucket_key_prefix = "s3://{}/{}".format(
    bucket, emr_ps_batch_output_key_prefix)


output_ps_batch_file_key = "{}/system/ps-ingest-data/batch-input/ps-complete-batch".format(prefix)


def sync_s3(file_name_list, s3_folder, local_folder):
    for f in file_name_list:
        print("file preparation: download src key {} to dst key {}".format(os.path.join(
            s3_folder, f), os.path.join(local_folder, f)))
        s3client.download_file(bucket, os.path.join(
            s3_folder, f), os.path.join(local_folder, f))


with SparkSession.builder.appName("Spark App - batch preprocessing").getOrCreate() as spark:
    #
    # process user file
    #
    print("start processing user file: {}".format(input_user_file))
    df_batch_input_raw = spark.read.text(input_user_file)
    # 52a23654-9dc3-11eb-a364-acde48001122_!_M_!_47_!_1615956929_!_lyingDove7
    df_batch_input = df_batch_input_raw.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 4).selectExpr("row[0] as userId")

    df_batch_output = df_batch_input.dropDuplicates(['userId']).select(to_json(struct("userId")).alias("userId"))

    df_batch_output.coalesce(1).write.mode("overwrite").option("header", "false").text(emr_ps_batch_output_bucket_key_prefix)


emr_ps_batch_output_file_key = list_s3_by_prefix(
    bucket,
    emr_ps_batch_output_key_prefix,
    lambda key: key.endswith(".txt"))[0]
print("emr_ps_batch_output_file_key:", emr_ps_batch_output_file_key)
s3_copy(bucket, emr_ps_batch_output_file_key, output_ps_batch_file_key)

print("output_ps_batch_file_key:", output_ps_batch_file_key)

print("All done")
