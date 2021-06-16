import json
import os
import time

import boto3
import requests

s3_client = None
sns_client = None

print('Loading function')


def s3_copy(from_bucket, to_bucket, from_key, to_key):
    print("copying s3://{}/{} to s3://{}/{}".format(from_bucket,
                                                    from_key, to_bucket, to_key))
    try:
        s3_client.copy_object(
            ACL='bucket-owner-full-control',
            CopySource={
                "Bucket": from_bucket,
                "Key": from_key
            },
            Metadata={
                'copyFrom': "s3://{}/{}".format(from_bucket, from_key)
            },
            MetadataDirective='REPLACE',
            Bucket=to_bucket,
            Key=to_key,
        )
        print("copied s3://{}/{} to s3://{}/{}".format(from_bucket,
                                                       from_key, to_bucket, to_key))
    except Exception as e:
        print(repr(e))


def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)
    global s3_client
    global sns_client
    s3_client = boto3.client('s3', config=config)
    sns_client = boto3.client('sns', config=config)


def lambda_handler(event, context):
    init()
    try:
        print("Received event: " + json.dumps(event, indent=2))
        return do_handler(event, context)
    except Exception as e:
        print(e)
        raise e


# aws s3 --profile aoyu ls s3://sagemaker-us-east-1-002224604296/"{}/feature/content/inverted-list/
# 2021-03-09 16:49:33    1530312 movie_actor_movie_ids_dict.pickle
# 2021-03-09 16:49:33     253313 movie_category_movie_ids_dict.pickle
# 2021-03-09 16:49:33     227094 movie_director_movie_ids_dict.pickle
# 2021-03-09 16:49:31    8213615 movie_id_movie_property_dict.pickle
# 2021-03-09 16:49:33     170828 movie_language_movie_ids_dict.pickle
# 2021-03-09 16:49:33      66353 movie_level_movie_ids_dict.pickle
# 2021-03-09 16:49:33     161824 movie_year_movie_ids_dict.pickle

stage = "dev"


def do_handler(event, context):
    sns_topic_arn = os.environ.get('SNS_TOPIC_ARN', '')
    online_loader_url = os.environ.get('ONLINE_LOADER_URL', '')
    global stage
    stage = os.environ.get('Stage', 'dev')

    print("sns_topic_arn='{}'".format(sns_topic_arn))
    print("online_loader_url='{}'".format(online_loader_url))

    bucket = event['Bucket']
    s3_key_prefix = event['S3Prefix']

    message_type = event.get('message_type', 'news')

    loader_url_env_name = message_type.upper() + '_ONLINE_LOADER_URL'
    if os.environ.get(loader_url_env_name, None):
        online_loader_url = os.environ.get(loader_url_env_name)
        print("env {}: online_loader_url='{}'".format(loader_url_env_name, online_loader_url))

    if len(online_loader_url) > 0 and not online_loader_url.endswith('loader/notice'):
        # online_loader_url is DNS name
        online_loader_url = os.path.join(online_loader_url, 'loader/notice')

    if len(online_loader_url) > 0 and not str(online_loader_url).startswith("http"):
        online_loader_url = "http://" + online_loader_url

    print("loader_url='{}'".format(online_loader_url))

    file_types = event['file_type'].split(",")

    if s3_key_prefix.endswith('/'):
        s3_key_prefix = s3_key_prefix[:-1]

    bucket_and_prefix = "s3://{}/{}".format(
        bucket, s3_key_prefix)
    print("bucket_and_prefix={}".format(bucket_and_prefix))

    msg_dict = get_message_dict(bucket_and_prefix, message_type)

    msg_file_types = []

    for file_type in file_types:
        if file_type == "action-new":
            msg_file_types.extend(["inverted-list"])
        elif file_type == "train-model":
            msg_file_types.extend(
                ["action-model", "embeddings", "vector-index"])
        elif file_type == "item-new":
            msg_file_types.extend(
                ["inverted-list", "embeddings", "vector-index", "action-model"])
            msg_file_types.append("{}_records".format(message_type))
        else:
            msg_file_types.append(file_type)

    print("msg_file_types: {}".format(msg_file_types))

    messages_sent = []
    for file_type in set(msg_file_types):
        print("send sns message for file_type: {}".format(file_type))

        notification_file_path = "{}/notification/{}/".format(
            bucket_and_prefix, file_type)
        file_names = []
        message = {
            # "region_id": region_id,
            "file_type": file_type,
            "file_path": "/".join(notification_file_path.split("/")[3:]),
            "file_name": file_names
        }

        for s3_file in msg_dict[file_type]:
            src_key = "/".join(s3_file.split("/")[3:])
            src_name = src_key.split("/")[-1]
            s3_copy(bucket, bucket, src_key, "{}{}".format(
                message['file_path'], src_name))
            file_names.append(src_name)

        if len(file_names) == 0:
            print("ignore {}".format(file_type))
            continue
        if sns_topic_arn:
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Message=json.dumps(message),
                Subject="RS Offline Notification",
                MessageAttributes={
                    "message_type": {
                        "DataType": "String",
                        "StringValue": str(message_type),
                    },
                    "file_type": {
                        "DataType": "String",
                        "StringValue": str(file_type),
                    }
                }
            )

        messages_sent.append(message)

        if online_loader_url:
            print("sleep 30 seconds (1) ...")
            time.sleep(30)
            post_request(online_loader_url,
                         {"message": message},
                         {'message_type': str(message_type)})
            print("sleep 30 seconds (2) ...")
            time.sleep(30)
            post_request(online_loader_url,
                         {"message": message},
                         {'message_type': str(message_type)})

    return success_response(json.dumps(messages_sent))


def post_request(loader_url, data, headers):
    print("loader_url: {}".format(loader_url))
    print("data: {}".format(json.dumps(data)))

    file_type = data['message']['file_type']
    demo_srv_url = loader_url.replace("loader/notice", f"api/v1/demo/notice")

    if file_type in ["movie_records", "news_records"]:
        url = demo_srv_url
    else:
        url = loader_url

    print("file_type: {}, url: {}".format(file_type, url))
    retry_count = 0
    while True:
        retry_count += 1
        try:
            r = requests.post(url, data=json.dumps(data), headers=headers)
            print("status_code: {}".format(r.status_code))
            return r.status_code
        except Exception as e:
            if retry_count > 3:
                break
            time.sleep(5)
            print("retry: {}, Error: {}".format(retry_count, repr(e)))


def get_message_dict(bucket_and_prefix, message_type):
    print("message_type: {}".format(message_type))
    movie_msg_dict = {
        "inverted-list": [
            "{}/feature/content/inverted-list/movie_actor_movie_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/movie_category_movie_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/movie_director_movie_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/movie_id_movie_property_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/movie_language_movie_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/movie_level_movie_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/movie_year_movie_ids_dict.pickle".format(
                bucket_and_prefix),

            "{}/feature/content/inverted-list/movie_id_movie_feature_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/action/embed_raw_item_mapping.pickle".format(
                bucket_and_prefix),
            "{}/feature/action/embed_raw_user_mapping.pickle".format(
                bucket_and_prefix),
            "{}/feature/action/raw_embed_item_mapping.pickle".format(
                bucket_and_prefix),
            "{}/feature/action/raw_embed_user_mapping.pickle".format(
                bucket_and_prefix),

            "{}/model/recall/recall_config.pickle".format(bucket_and_prefix),
            "{}/model/filter/filter_config.pickle".format(bucket_and_prefix),

            "{}/feature/recommend-list/portrait/portrait.pickle".format(
                bucket_and_prefix),
            "{}/feature/recommend-list/movie/recall_batch_result.pickle".format(
                bucket_and_prefix),
            "{}/feature/recommend-list/movie/rank_batch_result.pickle".format(
                bucket_and_prefix),
            "{}/feature/recommend-list/movie/filter_batch_result.pickle".format(
                bucket_and_prefix),
        ],
        "vector-index": [
            "{}/feature/action/ub_item_vector.index".format(bucket_and_prefix),
        ],
        "action-model": [
            "{}/model/rank/action/deepfm/latest/deepfm_model.tar.gz".format(
                bucket_and_prefix),
            "{}/model/recall/youtubednn/user_embeddings.h5".format(
                bucket_and_prefix),
        ],
        "embeddings": [
            "{}/feature/action/ub_item_embeddings.npy".format(
                bucket_and_prefix),
        ],

        "movie_records": [
            "{}/system/item-data/item.csv".format(
                bucket_and_prefix),
        ]

    }

    news_msg_dict = {
        "inverted-list": [
            "{}/feature/content/inverted-list/news_entities_news_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/news_id_news_feature_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/news_id_news_property_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/news_keywords_news_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/news_type_news_ids_dict.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/news_words_news_ids_dict.pickle".format(
                bucket_and_prefix),

            "{}/feature/content/inverted-list/recall_config.pickle".format(
                bucket_and_prefix),
            "{}/feature/content/inverted-list/filter_config.pickle".format(
                bucket_and_prefix),

            "{}/feature/action/embed_raw_item_mapping.pickle".format(
                bucket_and_prefix),
            "{}/feature/action/embed_raw_user_mapping.pickle".format(
                bucket_and_prefix),
            "{}/feature/action/raw_embed_item_mapping.pickle".format(
                bucket_and_prefix),
            "{}/feature/action/raw_embed_user_mapping.pickle".format(
                bucket_and_prefix),

            # "{}/model/recall/recall_config.pickle".format(bucket_and_prefix),
            # "{}/model/filter/filter_config.pickle".format(bucket_and_prefix),

            "{}/feature/recommend-list/portrait/portrait.pickle".format(
                bucket_and_prefix),
            "{}/feature/recommend-list/news/recall_batch_result.pickle".format(
                bucket_and_prefix),
            "{}/feature/recommend-list/news/rank_batch_result.pickle".format(
                bucket_and_prefix),
            "{}/feature/recommend-list/news/filter_batch_result.pickle".format(
                bucket_and_prefix),
        ],
        "vector-index": [
        ],
        "action-model": [
            "{}/model/rank/action/dkn/latest/model.tar.gz".format(
                bucket_and_prefix),

        ],
        "embeddings": [
            "{}/model/rank/content/dkn_embedding_latest/dkn_word_embedding.npy".format(
                bucket_and_prefix),
            "{}/model/rank/content/dkn_embedding_latest/dkn_context_embedding.npy".format(
                bucket_and_prefix),
            "{}/model/rank/content/dkn_embedding_latest/dkn_entity_embedding.npy".format(
                bucket_and_prefix),
            "{}/model/rank/content/dkn_embedding_latest/dkn_relation_embedding.npy".format(
                bucket_and_prefix),
        ],

        "news_records": [
            "{}/system/item-data/item.csv".format(
                bucket_and_prefix),
        ]
    }

    if message_type == 'movie':
        return movie_msg_dict
    if message_type == 'news':
        return news_msg_dict


def success_response(message):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": message
    }


def error_response(message):
    return {
        "statusCode": 400,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": message
    }
