import argparse
import os
import pickle

import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, size, row_number, expr, array_join
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql.window import Window


def list_s3_by_prefix(bucket, prefix, filter_func=None):
    if not prefix.endswith("/"):
        prefix = prefix + "/"
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

s3client = boto3.client('s3')

input_user_file = "s3://{}/{}/system/ingest-data/user/".format(bucket, prefix)
emr_user_output_key_prefix = "{}/system/emr/action-preprocessing/output/user".format(
    prefix)
emr_user_output_bucket_key_prefix = "s3://{}/{}".format(
    bucket, emr_user_output_key_prefix)
output_user_file_key = "{}/system/user-data/user.csv".format(prefix)

item_file = "s3://{}/{}/system/item-data/item.csv".format(bucket, prefix)

print("input_user_file:", input_user_file)

with SparkSession.builder.appName("Spark App - action preprocessing").getOrCreate() as spark:
    #
    # process user file
    #
    print("start processing user file: {}".format(input_user_file))
    df_user_input = spark.read.text(input_user_file)
    # 2361_!_M_!_57_!_1608411863_!_gutturalPie9
    df_user_input = df_user_input.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 4).selectExpr("row[0] as user_id",
                                         "row[1] as sex",
                                         "row[2] as age",
                                         "row[3] as timestamp",
                                         "row[4] as name",
                                         )
    df_user_input = df_user_input.dropDuplicates(['user_id'])
    total_user_count = df_user_input.count()
    print("total_user_count: {}".format(total_user_count))

    df_user_input.coalesce(1).write.mode("overwrite").option(
        "header", "false").option("sep", "_!_").csv(emr_user_output_bucket_key_prefix)

emr_user_output_file_key = list_s3_by_prefix(
    bucket,
    emr_user_output_key_prefix,
    lambda key: key.endswith(".csv"))[0]
print("emr_user_output_file_key:", emr_user_output_file_key)
s3_copy(bucket, emr_user_output_file_key, output_user_file_key)
print("output_user_file_key:", output_user_file_key)

print("All done")
