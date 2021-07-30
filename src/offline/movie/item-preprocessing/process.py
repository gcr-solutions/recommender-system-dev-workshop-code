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

output_file_key = "{}/system/item-data/item.csv".format(prefix)

with SparkSession.builder.appName("Spark App - item preprocessing").getOrCreate() as spark:
    # This is needed to save RDDs which is the only way to write nested Dataframes into CSV format
    # spark.sparkContext._jsc.hadoopConfiguration().set("mapred.output.committer.class",
    #                                                   "org.apache.hadoop.mapred.FileOutputCommitter")
    Timer1 = time.time()

    #
    # process item file
    #

    df_input = spark.read.text(input_file)
    # program_id|program_type|program_name|release_year|director|actor|category_property|language|ticket_num|popularity|score|level|new_series
    df_input = df_input.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 12).selectExpr("row[0] as program_id",
                                          "row[1] as program_type",
                                          "row[2] as program_name",
                                          "row[3] as release_year",
                                          "row[4] as director",
                                          "row[5] as actor",
                                          "row[6] as category_property",
                                          "row[7] as language",
                                          "row[8] as ticket_num",
                                          "row[9] as popularity",
                                          "row[10] as score",
                                          "row[11] as level",
                                          "row[12] as is_new"
                                          )
    df_input_1 = df_input.withColumn("is_new_int", expr("cast(is_new as int)"))
    # for column is_new: 0 will overwrite 1
    df_is_new = df_input_1.groupby("program_id").min('is_new_int')
    df_final = df_input_1.join(df_is_new, ["program_id"]).select("program_id",
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
                                                                 "min(is_new_int)"
                                                                 ).dropDuplicates(["program_id"])
    df_final.coalesce(1).write.mode("overwrite").option(
        "header", "false").option("sep", "_!_").csv(emr_output_bucket_key_prefix)

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
