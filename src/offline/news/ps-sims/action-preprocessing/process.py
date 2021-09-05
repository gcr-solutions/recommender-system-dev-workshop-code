import argparse
import os
import pickle

import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, size, row_number, expr, array_join, lit
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql.window import Window


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
parser.add_argument("--only4popularity", type=str, default='0',
                    help="only4popularity")

parser.add_argument("--region", type=str, help="aws region")
args, _ = parser.parse_known_args()
print("args:", args)

if args.region:
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix
only4popularity = False

if int(args.only4popularity) > 0:
    print("only4popularity is True")
    only4popularity = True

if prefix.endswith("/"):
    prefix = prefix[:-1]

print(f"bucket:{bucket}, prefix:{prefix}, only4popularity: {only4popularity}")

input_action_file = "s3://{}/{}/system/ingest-data/action/".format(
    bucket, prefix)
emr_action_output_key_prefix = "{}/system/emr/action-preprocessing/output/action".format(
    prefix)
emr_action_output_bucket_key_prefix = "s3://{}/{}".format(
    bucket, emr_action_output_key_prefix)
emr_ps_action_output_key_prefix = "{}/system/emr/action-preprocessing/output/ps-action".format(
    prefix)
emr_ps_action_output_bucket_key_prefix = "s3://{}/{}".format(
    bucket, emr_ps_action_output_key_prefix)

output_action_file_key = "{}/system/action-data/action.csv".format(prefix)
output_ps_action_file_key = "{}/system/ps-ingest-data/action/ps_action.csv".format(prefix)

item_file = "s3://{}/{}/system/item-data/item.csv".format(bucket, prefix)
user_file = "s3://{}/{}/system/user-data/user.csv".format(bucket, prefix)


emr_action_popularity_output_key_prefix = "{}/system/emr/action-preprocessing/output/popularity-action".format(
    prefix)
emr_action_popularity_output_bucket_key_prefix = "s3://{}/{}".format(
    bucket, emr_action_popularity_output_key_prefix)
output_action_popularity_file_key = "{}/system/popularity-action-data/action.csv".format(prefix)

print("input_action_file:", input_action_file)
if only4popularity:
    print("only update only4popularity file:", output_action_popularity_file_key)
else:
    print("item_file:", item_file)
    print("user_file:", user_file)


def sync_s3(file_name_list, s3_folder, local_folder):
    for f in file_name_list:
        print("file preparation: download src key {} to dst key {}".format(os.path.join(
            s3_folder, f), os.path.join(local_folder, f)))
        s3client.download_file(bucket, os.path.join(
            s3_folder, f), os.path.join(local_folder, f))


with SparkSession.builder.appName("Spark App - action preprocessing").getOrCreate() as spark:
    #
    # process action file
    #
    print("start processing action file: {}".format(input_action_file))
    # 52a23654-9dc3-11eb-a364-acde48001122_!_6552302645908865543_!_1618455260_!_1_!_0
    df_action_input_raw = spark.read.text(input_action_file)
    df_action_input = df_action_input_raw.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 4).selectExpr("row[0] as user_id",
                                         "row[1] as item_id",
                                         "row[2] as timestamp",
                                         "row[3] as action_type",
                                         "cast(row[4] as string) as action_value",
                                         )
    ps_df_action_input = df_action_input_raw.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 4).selectExpr("row[0] as USER_ID",
                                         "row[1] as ITEM_ID",
                                         "row[2] as TIMESTAMP",
                                         "row[3] as EVENT_TYPE",
                                         "cast(row[4] as string) as EVENT_VALUE",
                                         ).withColumn("EVENT_TYPE", lit("CLICK"))
    df_action_input.cache()
    ps_df_action_input.cache()

    if only4popularity:
        df_action_input \
            .select("user_id", "item_id", "timestamp", "action_type", "action_value") \
            .coalesce(1).write.mode("overwrite") \
            .option("header", "false").option("sep", "_!_").csv(emr_action_popularity_output_bucket_key_prefix)
    else:
        df_item = spark.read.text(item_file)
        df_item_id = df_item.selectExpr("split(value, '_!_') as row").where(
            size(col("row")) > 6).selectExpr("row[0] as item_id")
        ps_df_item_id = df_item.selectExpr("split(value, '_!_') as row").where(
            size(col("row")) > 6).selectExpr("row[0] as ITEM_ID")

        df_user = spark.read.text(user_file)
        df_user_id = df_user.selectExpr("split(value, '_!_') as row").where(
            size(col("row")) > 4).selectExpr("row[0] as user_id")
        ps_df_user_id = df_user.selectExpr("split(value, '_!_') as row").where(
            size(col("row")) > 4).selectExpr("row[0] as USER_ID")

        df_action_output = df_action_input.join(df_item_id, ['item_id']).join(df_user_id, ['user_id'])
        ps_df_action_output = ps_df_action_input.join(ps_df_item_id, ['ITEM_ID']).join(ps_df_user_id, ['USER_ID'])

        action_count = df_action_output.count()
        print("action_count: {}".format(action_count))
        df_action_output \
            .select("user_id", "item_id", "timestamp", "action_type", "action_value") \
            .coalesce(1).write.mode("overwrite") \
            .option("header", "false").option("sep", "_!_").csv(emr_action_output_bucket_key_prefix)

        ps_df_action_output \
            .select("USER_ID", "ITEM_ID", "TIMESTAMP", "EVENT_TYPE") \
            .coalesce(1).write.mode("overwrite") \
            .option("header", "true").option("sep", ",").csv(emr_ps_action_output_bucket_key_prefix)

if only4popularity:
    emr_action_popularity_output_file_key = list_s3_by_prefix(
        bucket,
        emr_action_popularity_output_key_prefix,
        lambda key: key.endswith(".csv"))[0]
    print("emr_action_popularity_output_file_key:", emr_action_popularity_output_file_key)
    s3_copy(bucket, emr_action_popularity_output_file_key, output_action_popularity_file_key)
    print("output_action_popularity_file_key:", output_action_popularity_file_key)
else:
    emr_action_output_file_key = list_s3_by_prefix(
        bucket,
        emr_action_output_key_prefix,
        lambda key: key.endswith(".csv"))[0]
    print("emr_action_output_file_key:", emr_action_output_file_key)
    s3_copy(bucket, emr_action_output_file_key, output_action_file_key)
    print("output_action_file_key:", output_action_file_key)

    emr_ps_action_output_file_key = list_s3_by_prefix(
        bucket,
        emr_ps_action_output_key_prefix,
        lambda key: key.endswith(".csv"))[0]
    print("emr_ps_action_output_file_key:", emr_ps_action_output_file_key)
    s3_copy(bucket, emr_ps_action_output_file_key, output_ps_action_file_key)
    print("output_ps_action_file_key:", output_ps_action_file_key)

print("All done")
