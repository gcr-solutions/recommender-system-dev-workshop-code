import argparse
import os
import pickle
import json
import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, size, row_number, expr, array_join, from_json
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, IntegerType
import pyspark.sql.functions as F
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


parser = argparse.ArgumentParser(description="app inputs and outputs")
parser.add_argument("--bucket", type=str, help="s3 bucket")
parser.add_argument("--prefix", type=str,
                    help="s3 input key prefix")
parser.add_argument("--region", type=str, help="aws region")
parser.add_argument("--n_days", type=int, default=99999, help="history data used to train model")
parser.add_argument("--method", type=str, default='customize', help="method name")

args, _ = parser.parse_known_args()
print("args:", args)

if args.region:
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix
if prefix.endswith("/"):
    prefix = prefix[:-1]
method = args.method
n_days = args.n_days

print(f"bucket:{bucket}, prefix:{prefix}")

s3client = boto3.client('s3')

input_action_file = "s3://{}/{}/system/ingest-data/action/".format(
    bucket, prefix)

emr_train_action_key_prefix = "{}/system/emr/action-preprocessing/output/train_action".format(
    prefix)
emr_s3_train_output = "s3://{}/{}".format(bucket, emr_train_action_key_prefix)
output_action_train_key = "{}/system/action-data/action_train.csv".format(
    prefix)

emr_ps_action_output_key_prefix = "{}/system/emr/action-preprocessing/output/ps-action".format(
    prefix)
emr_ps_action_output_bucket_key_prefix = "s3://{}/{}".format(
    bucket, emr_ps_action_output_key_prefix)

emr_val_action_key_prefix = "{}/system/emr/action-preprocessing/output/val_action".format(
    prefix)
emr_s3_val_output = "s3://{}/{}".format(bucket, emr_val_action_key_prefix)
output_action_val_key = "{}/system/action-data/action_val.csv".format(prefix)
output_ps_action_file_key = "{}/system/ps-ingest-data/action/ps_action.csv".format(prefix)

print("input_action_file:", input_action_file)

N = 8


class UdfFunction:
    @staticmethod
    def build_sort_click_hist(entities_list, words_list, action_value_list, item_id_list, timestamp_list):
        pairs = []
        for e, w, a, it, tm in zip(entities_list, words_list, action_value_list, item_id_list, timestamp_list):
            pairs.append((e, w, a, it, tm))
        pairs = sorted(pairs, key=lambda x: x[-1] * 10 + int(x[2]))
        result_arr = []
        clicked_entities_hist = []
        clicked_words_hist = []
        clicked_items_hist = []
        for i in range(len(pairs)):
            item_id = pairs[i][3]
            timestamp = pairs[i][-1]

            clicked_items_hist_len = len(clicked_items_hist)
            if pairs[i][2] == '1':
                clicked_entities_hist.append(str(pairs[i][0]))
                clicked_words_hist.append(str(pairs[i][1]))
                clicked_items_hist.append(str(item_id))

            el = json.dumps({
                "clicked_entities_arr":
                    clicked_entities_hist[clicked_items_hist_len - N: clicked_items_hist_len].copy(),
                "clicked_words_arr":
                    clicked_words_hist[clicked_items_hist_len - N: clicked_items_hist_len].copy(),
                "clicked_items_arr":
                    clicked_items_hist[clicked_items_hist_len - N: clicked_items_hist_len].copy(),
                "item_id": item_id,
                "timestamp": timestamp,
            })
            result_arr.append(el)

        return result_arr


def sync_s3(file_name_list, s3_folder, local_folder):
    for f in file_name_list:
        print("file preparation: download src key {} to dst key {}".format(os.path.join(
            s3_folder, f), os.path.join(local_folder, f)))
        s3client.download_file(bucket, os.path.join(
            s3_folder, f), os.path.join(local_folder, f))


def gen_train_dataset(train_dataset_input):
    build_sort_click_hist = F.udf(UdfFunction.build_sort_click_hist, ArrayType(StringType()))
    clicked_schema = StructType([
        StructField('clicked_entities_arr', ArrayType(StringType()), False),
        StructField('clicked_words_arr', ArrayType(StringType()), False),
        StructField('clicked_items_arr', ArrayType(StringType()), False),
        StructField('item_id', StringType(), False),
        StructField('timestamp', IntegerType(), False)
    ])
    train_clicked_entities_words_arr_df = train_dataset_input \
        .groupby('user_id') \
        .agg(
        build_sort_click_hist(
            F.collect_list("entities"),
            F.collect_list("words"),
            F.collect_list("action_value"),
            F.collect_list("item_id"),
            F.collect_list("timestamp")).alias('clicked_hist_arr')) \
        .select('user_id', F.explode(col('clicked_hist_arr')).alias('clicked_hist')) \
        .withColumn('json_col', from_json('clicked_hist', clicked_schema)) \
        .select('user_id', "json_col.*")
    train_entities_words_df = train_clicked_entities_words_arr_df \
        .withColumn("clicked_entities",
                    array_join(col('clicked_entities_arr'), "-")) \
        .withColumn("clicked_words",
                    array_join(col('clicked_words_arr'), "-")) \
        .withColumn("clicked_item_ids",
                    array_join(col('clicked_items_arr'), "-")) \
        .drop("clicked_entities_arr") \
        .drop("clicked_words_arr") \
        .drop("clicked_items_arr")
    join_type = "left_outer"
    dataset_final = train_dataset_input \
        .join(train_entities_words_df, on=["user_id", "item_id", "timestamp"], how=join_type) \
        .select(
        "user_id", "words", "entities",
        "action_value", "clicked_words",
        "clicked_entities", "item_id", "timestamp", "clicked_item_ids") \
        .dropDuplicates(['user_id', 'item_id', 'timestamp', 'action_value'])

    return dataset_final


def load_feature_dict(feat_dict_file):
    print("load_feature_dict:{}".format(feat_dict_file))
    with open(feat_dict_file, 'rb') as input:
        feat_dict = pickle.load(input)
    f_list = []
    for k, v in feat_dict.items():
        item_id = k
        entities = ",".join([str(it) for it in v['entities']])
        words = ",".join([str(it) for it in v['words']])
        f_list.append([item_id, entities, words])
    return f_list


def load_user_dict(user_id_map_file):
    print("load_user_dict: {}".format(user_id_map_file))
    with open(user_id_map_file, 'rb') as input:
        feat_dict = pickle.load(input)
    u_list = []
    for k, v in feat_dict.items():
        user_id = str(k)
        ml_user_id = str(v)
        u_list.append([user_id, ml_user_id])
    return u_list


local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
files_to_load = ["news_id_news_feature_dict.pickle"]
sync_s3(files_to_load,
        "{}/feature/content/inverted-list/".format(prefix),
        local_folder)
feat_list = load_feature_dict(os.path.join(
    local_folder, "news_id_news_feature_dict.pickle"))
print("feat_list len:{}".format(len(feat_list)))

files_to_load = ["raw_embed_user_mapping.pickle"]
sync_s3(files_to_load,
        "{}/feature/action/".format(prefix),
        local_folder)
user_list = load_user_dict(os.path.join(
    local_folder, "raw_embed_user_mapping.pickle"))
print("user_list len:{}".format(len(user_list)))

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
                                         "cast(row[2] as int) as timestamp",
                                         "row[3] as action_type",
                                         "cast(row[4] as string) as action_value",
                                         ).dropDuplicates(['user_id', 'item_id', 'timestamp', 'action_type'])
    df_action_input.cache()
    #
    # data for training
    #

    schema = StructType([
        StructField('item_id', StringType(), False),
        StructField('entities', StringType(), False),
        StructField('words', StringType(), False)
    ])
    user_map_schema = StructType([
        StructField('user_id', StringType(), False),
        StructField('ml_user_id', StringType(), False),
    ])

    df_feat = spark.createDataFrame(feat_list, schema).dropDuplicates(['item_id'])
    df_user_id_map = spark.createDataFrame(user_list, user_map_schema).dropDuplicates(['user_id'])

    max_timestamp = df_action_input.selectExpr("max(timestamp)").collect()[0]["max(timestamp)"]
    df_action_input_latest = df_action_input.where(col('timestamp') > max_timestamp - 24 * 3600 * n_days)
    min_timestamp = df_action_input_latest.selectExpr("min(timestamp)").collect()[0]["min(timestamp)"]
    print("min_timestamp: {}, max_timestamp: {}".format(min_timestamp, max_timestamp))

    df_action_with_feat = df_action_input_latest.join(df_feat, on=['item_id'])
    df_action_with_clicked_hist = gen_train_dataset(df_action_with_feat)

    if max_timestamp - min_timestamp > 24 * 3600 * 10:
        split_timestamp = max_timestamp - 24 * 3600 * 2
        print("more than 10 days, split_timestamp: {}, keep 2 days as val".format(split_timestamp))
    else:
        split_timestamp = int((max_timestamp - min_timestamp) * 0.8 + min_timestamp)
        print("less 10 days, split_timestamp: {}, keep 0.2 as val".format(split_timestamp))

    train_dataset = df_action_with_clicked_hist.where(col('timestamp') <= split_timestamp)
    val_dataset = df_action_with_clicked_hist.where(col('timestamp') > split_timestamp)

    train_count = train_dataset.count()
    val_count = val_dataset.count()
    print("train_count: {}, val_count: {}".format(train_count, val_count))

    # if val_count < 10 or val_count > train_count:
    #     print("train_count: {}, val_count: {}, use randomSplit[0.7, 0.3]".format(train_count, val_count))
    #     train_dataset, val_dataset = df_action_with_clicked_hist.randomSplit([0.8, 0.2], seed=42)

    # window_spec = Window.orderBy('timestamp')
    # timestamp_num = row_number().over(window_spec)
    # timestamp_ordered_df = df_action_input_latest.select('timestamp').distinct().withColumn("timestamp_num", timestamp_num)
    # timestamp_ordered_df.cache()
    # max_timestamp_num = timestamp_ordered_df.selectExpr("max(timestamp_num)").collect()[0]['max(timestamp_num)']
    #
    # df_action_input_ordered = df_action_input_latest.join(timestamp_ordered_df, on=['timestamp'])
    #
    # split_timestamp_num = int(max_timestamp_num * 0.7)
    # if max_timestamp_num > 10000:
    #     split_timestamp_num = max_timestamp_num - 1500
    #
    # train_dataset = df_action_input_ordered.where(col('timestamp_num') <= split_timestamp_num).drop('timestamp_num')
    # val_dataset = df_action_input_ordered.where(col('timestamp_num') > split_timestamp_num).drop('timestamp_num')

    #
    # gen train dataset
    #
    train_dataset_final = train_dataset.join(df_user_id_map, on=["user_id"]).select(
        "ml_user_id", "words", "entities",
        "action_value", "clicked_words",
        "clicked_entities", "item_id", "timestamp"
    )

    train_dataset_final.coalesce(1).write.mode("overwrite").option(
        "header", "false").option("sep", "\t").csv(emr_s3_train_output)

    #
    # gen val dataset
    #
    val_dataset_final = val_dataset.join(df_user_id_map, on=["user_id"]).select(
        "ml_user_id", "words", "entities",
        "action_value", "clicked_words",
        "clicked_entities", "item_id", "timestamp"
    )

    val_dataset_final.coalesce(1).write.mode("overwrite").option(
        "header", "false").option("sep", "\t").csv(emr_s3_val_output)

    if method != "customize":
        df_ps_action_input = df_action_input_raw.selectExpr("split(value, '_!_') as row").where(
            size(col("row")) > 4).selectExpr("row[0] as USER_ID",
                                             "row[1] as ITEM_ID",
                                             "row[2] as TIMESTAMP",
                                             "row[3] as EVENT_TYPE",
                                             "cast(row[4] as string) as EVENT_VALUE",
                                             )
        df_ps_action_input.cache()
        df_ps_action_input \
            .select("USER_ID", "ITEM_ID", "TIMESTAMP", "EVENT_TYPE") \
            .coalesce(1).write.mode("overwrite") \
            .option("header", "true").option("sep", ",").csv(emr_ps_action_output_bucket_key_prefix)

train_action_key = list_s3_by_prefix(
    bucket,
    emr_train_action_key_prefix,
    lambda key: key.endswith(".csv"))[0]
print("train_action_key:", train_action_key)
s3_copy(bucket, train_action_key, output_action_train_key)
print("output_action_train_key:", output_action_train_key)

val_action_key = list_s3_by_prefix(
    bucket,
    emr_val_action_key_prefix,
    lambda key: key.endswith(".csv"))[0]
print("val_action_key:", val_action_key)
s3_copy(bucket, val_action_key, output_action_val_key)
print("output_action_val_key:", output_action_val_key)

if method != "customize":
    emr_ps_action_output_file_key = list_s3_by_prefix(
        bucket,
        emr_ps_action_output_key_prefix,
        lambda key: key.endswith(".csv"))[0]
    print("emr_ps_action_output_file_key:", emr_ps_action_output_file_key)
    s3_copy(bucket, emr_ps_action_output_file_key, output_ps_action_file_key)
    print("output_ps_action_file_key:", output_ps_action_file_key)

print("All done")
