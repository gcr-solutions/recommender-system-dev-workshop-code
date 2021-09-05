import argparse
import time

import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, size, regexp_replace, expr


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

# input_prefix=recommender-system-news-open-toutiao/system/item-data/raw-input/
# output_prefix=recommender-system-news-open-toutiao/system/item-data/emr-out/

input_file = "s3://{}/{}/system/ingest-data/item/".format(bucket, prefix)
emr_output_key_prefix = "{}/system/emr/item-preprocessing/output/".format(prefix)
emr_output_bucket_key_prefix = "s3://{}/{}".format(bucket, emr_output_key_prefix)

emr_ps_output_key_prefix = "{}/system/emr/item-preprocessing/ps-output/".format(prefix)
emr_ps_output_bucket_key_prefix = "s3://{}/{}".format(bucket, emr_ps_output_key_prefix)

output_file_key = "{}/system/item-data/item.csv".format(prefix)
output_ps_file_key = "{}/system/ps-ingest-data/item/ps_item.csv".format(prefix)

print("input_file:", input_file)
print("debug sig")
filter_chars = r'[&`><=@ω\{\}^#$/\]\[*【】Ⅴ；%+——「」｜…….:。\s？.：·、！《》!,，_~)）（(?“”"\\-]'

input_user_file = "s3://{}/{}/system/ingest-data/user/".format(bucket, prefix)
emr_user_output_key_prefix = "{}/system/emr/action-preprocessing/output/user".format(prefix)
emr_user_output_bucket_key_prefix = "s3://{}/{}".format(bucket, emr_user_output_key_prefix)
output_user_file_key = "{}/system/user-data/user.csv".format(prefix)
output_ps_user_file_key = "{}/system/ps-ingest-data/user/user.csv".format(prefix)

with SparkSession.builder.appName("Spark App - item preprocessing").getOrCreate() as spark:
    # This is needed to save RDDs which is the only way to write nested Dataframes into CSV format
    # spark.sparkContext._jsc.hadoopConfiguration().set("mapred.output.committer.class",
    #                                                   "org.apache.hadoop.mapred.FileOutputCommitter")
    Timer1 = time.time()

    #
    # process item file
    #

    df_input_raw = spark.read.text(input_file)
    # 6552418723179790856_!_102_!_news_entertainment_!_谢娜三喜临门何炅送祝福吴昕送祝福只有沈梦辰不一样_!_杜海涛,谢娜,何炅,沈梦辰,吴昕,快本_!_3_!_0
    df_input = df_input_raw.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 6).selectExpr("row[0] as id",
                                         "row[1] as item_type_code",
                                         "row[2] as item_type",
                                         "row[3] as title_raw",
                                         "row[4] as keywords",
                                         "row[5] as popularity",
                                         "row[6] as is_new"
                                         )
    df_ps_input = df_input_raw.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 6).selectExpr("row[0] as ITEM_ID",
                                         "row[1] as item_type_code",
                                         "row[2] as CATEGORY",
                                         "row[3] as title_raw",
                                         "row[4] as keywords",
                                         "row[5] as popularity",
                                         "row[6] as is_new"
                                         )

    df_input = df_input.where("keywords != ''")
    df_input = df_input.select(col("id"),
                               col("item_type_code"),
                               col("item_type"),
                               regexp_replace(col("title_raw"), filter_chars, '').alias('title'),
                               col("keywords"),
                               col("popularity"),
                               col("is_new")
                               )
    df_ps_input = df_ps_input.where("keywords != ''")
    df_ps_input = df_ps_input.select(col("ITEM_ID"),
                               col("CATEGORY"),
                               regexp_replace(col("keywords"), ',', '|').alias('KEYWORD'),
                               )

    df_input_1 = df_input.withColumn("is_new_int", expr("cast(is_new as int)"))
    # for column is_new: 0 will overwrite 1
    df_is_new = df_input_1.groupby("id").min('is_new_int')
    df_title = df_input_1.join(df_is_new, ["id"]).select("id", "item_type_code",
                                                         "item_type", "title",
                                                         "keywords", "popularity",
                                                         "min(is_new_int)"
                                                         ).dropDuplicates(["id"])
    df_final = df_title.dropDuplicates(['title'])
    df_final.coalesce(1).write.mode("overwrite").option(
        "header", "false").option("sep", "_!_").csv(emr_output_bucket_key_prefix)

    df_ps_final = df_ps_input.dropDuplicates(['ITEM_ID'])
    df_ps_final.coalesce(1).write.mode("overwrite").option(
        "header", "true").option("sep", ",").csv(emr_ps_output_bucket_key_prefix)

    #
    # process user file
    #
    # print("start processing user file: {}".format(input_user_file))
    # df_user_input = spark.read.text(input_user_file)
    # # 52a23654-9dc3-11eb-a364-acde48001122_!_M_!_47_!_1615956929_!_lyingDove7
    # df_user_input = df_user_input.selectExpr("split(value, '_!_') as row").where(
    #     size(col("row")) > 4).selectExpr("row[0] as user_id",
    #                                      "row[1] as sex",
    #                                      "row[2] as age",
    #                                      "row[3] as timestamp",
    #                                      "row[4] as name",
    #                                      )
    # df_user_input = df_user_input.dropDuplicates(['user_id'])
    # df_user_input.coalesce(1).write.mode("overwrite").option(
    #     "header", "false").option("sep", "_!_").csv(emr_user_output_bucket_key_prefix)

    print("It take {:.2f} minutes to finish".format(
        (time.time() - Timer1) / 60))

#
# item file
#
emr_output_file_key = list_s3_by_prefix(
    bucket,
    emr_output_key_prefix,
    lambda key: key.endswith(".csv"))[0]

print("emr_output_file_key:", emr_output_file_key)
s3_copy(bucket, emr_output_file_key, output_file_key)
print("output file:", output_file_key)

emr_ps_output_file_key = list_s3_by_prefix(
    bucket,
    emr_ps_output_key_prefix,
    lambda key: key.endswith(".csv"))[0]

print("emr_ps_output_file_key:", emr_ps_output_file_key)
s3_copy(bucket, emr_ps_output_file_key, output_ps_file_key)
print("output file:", output_ps_file_key)

#
# user file
#
# emr_user_output_file_key = list_s3_by_prefix(
#     bucket,
#     emr_user_output_key_prefix,
#     lambda key: key.endswith(".csv"))[0]
# print("emr_user_output_file_key:", emr_user_output_file_key)
# s3_copy(bucket, emr_user_output_file_key, output_user_file_key)
#
# print("output_user_file_key:", output_user_file_key)
