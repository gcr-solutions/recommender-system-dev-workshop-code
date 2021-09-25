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

parser.add_argument("--only4training", type=str, default="0",
                    help="set to '1' if gen file [train_action.csv] only for training")

parser.add_argument("--region", type=str, help="aws region")
args, _ = parser.parse_known_args()
print("args:", args)

if args.region:
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix
only4training = False

if int(args.only4training) > 0:
    only4training = True

if prefix.endswith("/"):
    prefix = prefix[:-1]

print(f"bucket:{bucket}, prefix:{prefix}")

s3client = boto3.client('s3')

input_action_file = "s3://{}/{}/system/ingest-data/action/".format(
    bucket, prefix)
emr_action_output_key_prefix = "{}/system/emr/action-preprocessing/output/action".format(
    prefix)

output_action_file_key = "{}/system/action-data/action.csv".format(prefix)

if only4training:
    emr_action_output_key_prefix = "{}/system/emr/action-preprocessing/output/train-action".format(
        prefix)
    output_action_file_key = "{}/system/action-data/train_action.csv".format(prefix)

emr_action_output_bucket_key_prefix = "s3://{}/{}".format(
    bucket, emr_action_output_key_prefix)

item_file = "s3://{}/{}/system/item-data/item.csv".format(bucket, prefix)
user_file = "s3://{}/{}/system/user-data/user.csv".format(bucket, prefix)

print("input_action_file:", input_action_file)
print("item_file:", item_file)
print("user_file:", user_file)
print("only4training:", only4training)
print("emr_action_output_key_prefix:", emr_action_output_key_prefix)
print("output_action_file_key:", output_action_file_key)

with SparkSession.builder.appName("Spark App - action preprocessing").getOrCreate() as spark:
    #
    # read item file
    #
    df_item = spark.read.text(item_file)
    df_item = df_item.selectExpr("split(value, '_!_') as row") \
        .selectExpr("row[0] as program_id",
                    "row[1] as program_type",
                    "row[2] as program_name",
                    "row[3] as release_year",
                    "row[4] as director",
                    "row[5] as actor",
                    "row[6] as category_property",  # or genres
                    "row[7] as language",
                    "row[8] as ticket_num",
                    "row[9] as popularity",
                    "row[10] as score",
                    "row[11] as level",
                    "row[12] as is_new"
                    ).dropDuplicates(["program_id"])
    df_item.cache()
    total_item_count = df_item.count()
    print("total_item_count: {}".format(total_item_count))
    df_item_id = df_item.select("program_id")

    #
    # read user file
    #
    df_user_input = spark.read.text(user_file)
    # 2361_!_M_!_57_!_1608411863_!_gutturalPie9
    df_user_input = df_user_input.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 4).selectExpr("row[0] as user_id",
                                         "row[1] as sex",
                                         "row[2] as age",
                                         "row[3] as timestamp",
                                         "row[4] as name",
                                         )

    #
    # process action file
    #
    print("start processing action file: {}".format(input_action_file))
    # 18892_!_534_!_1617862565_!_1_!_0_!_1
    df_action_input = spark.read.text(input_action_file)
    df_action_input = df_action_input.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 5).selectExpr("row[0] as user_id",
                                         "row[1] as item_id",
                                         "row[2] as timestamp",
                                         "cast(row[3] as string) as action_type",
                                         "row[4] as action_value",
                                         "row[5] as click_source",
                                         )

    df_action_input = df_action_input.join(df_item_id, df_action_input["item_id"] == df_item_id["program_id"], "inner") \
        .select("user_id", "item_id", "action_type", "action_value", "timestamp")
    df_action_input.cache()
    total_action_count = df_action_input.count()
    print("after jon df_item, total_action_count: {}".format(total_action_count))

    #
    # filter the user_id that not in df_user_input
    #
    df_action_input = df_action_input.withColumnRenamed("user_id", "action_user_id")
    df_user_input = df_user_input.withColumnRenamed("timestamp", "user_timestamp")
    df_action_input.join(df_user_input, df_action_input['action_user_id'] == df_user_input['user_id'], "inner") \
        .select('user_id', "item_id", "action_type", "action_value", "timestamp")
    total_action_count = df_action_input.count()
    print("after jon df_user_input, total_action_count: {}".format(total_action_count))

    df_action_input.coalesce(1).write.mode("overwrite").option(
        "header", "false").option("sep", "_!_").csv(emr_action_output_bucket_key_prefix)

emr_action_output_file_key = list_s3_by_prefix(
    bucket,
    emr_action_output_key_prefix,
    lambda key: key.endswith(".csv"))[0]
print("emr_action_output_file_key:", emr_action_output_file_key)
s3_copy(bucket, emr_action_output_file_key, output_action_file_key)
print("output_action_file_key:", output_action_file_key)

print("All done")
