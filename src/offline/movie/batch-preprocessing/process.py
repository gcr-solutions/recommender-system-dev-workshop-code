import argparse
import time

import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, size, regexp_replace, expr, to_json, struct


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


input_file = "s3://{}/{}/system/ingest-data/item/".format(bucket, prefix)
emr_output_key_prefix = "{}/system/emr/batch-preprocessing/output/ps-sims-batch".format(prefix)
emr_output_bucket_key_prefix = "s3://{}/{}".format(bucket, emr_output_key_prefix)

output_file_key = "{}/system/ps-ingest-data/batch-input/ps-sims-batch".format(prefix)

print("input_file:", input_file)
print("debug sig")
filter_chars = r'[&`><=@ω\{\}^#$/\]\[*【】Ⅴ；%+——「」｜…….:。\s？.：·、！《》!,，_~)）（(?“”"\\-]'

with SparkSession.builder.appName("Spark App - item preprocessing").getOrCreate() as spark:
    # This is needed to save RDDs which is the only way to write nested Dataframes into CSV format
    # spark.sparkContext._jsc.hadoopConfiguration().set("mapred.output.committer.class",
    #                                                   "org.apache.hadoop.mapred.FileOutputCommitter")
    Timer1 = time.time()

    #
    # process item file
    #

    df_input_raw = spark.read.text(input_file)
    df_batch_input = df_input_raw.selectExpr("split(value, '_!_') as row").where(
        size(col("row")) > 6).selectExpr("row[0] as itemId"
                                         )

    df_batch_output = df_batch_input.dropDuplicates(['itemId']).select(to_json(struct("itemId")).alias("itemId"))

    df_batch_output.coalesce(1).write.mode("overwrite").option("header", "false").text(emr_output_bucket_key_prefix)

    print("It take {:.2f} minutes to finish".format(
        (time.time() - Timer1) / 60))

#
# item file
#
emr_output_file_key = list_s3_by_prefix(
    bucket,
    emr_output_key_prefix,
    lambda key: key.endswith(".txt"))[0]

print("emr_output_file_key:", emr_output_file_key)
s3_copy(bucket, emr_output_file_key, output_file_key)
print("output file:", output_file_key)

