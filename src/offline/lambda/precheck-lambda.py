import json
import os
import time

import boto3

print('Loading function')

s3_client = None


def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)
    global s3_client
    s3_client = boto3.client('s3', config=config)


def lambda_handler(event, context):
    init()
    try:
        print("Received event: " + json.dumps(event, indent=2))
        return do_handler(event, context)
    except Exception as e:
        print(e)
        raise e


def list_s3_by_prefix(bucket, key_prefix, filter_func=None):
    next_token = ''
    all_keys = []
    while True:
        if next_token:
            res = s3_client.list_objects_v2(
                Bucket=bucket,
                ContinuationToken=next_token,
                Prefix=key_prefix)
        else:
            res = s3_client.list_objects_v2(
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


def filter_key(key):
    name = s3_base_name(key).lower()
    if "readme" in name:
        return False
    if name.startswith("_"):
        return False
    return True


def s3_key_exists(bucket, key):
    try:
        res = s3_client.head_object(
            Bucket=bucket,
            Key=key,
        )
    except Exception:
        return False
    if res:
        return True
    return False


def do_handler(event, context):
    bucket = event['bucket']
    prefix = event.get("prefix", "")
    if prefix.endswith("/"):
        prefix = prefix[:-1]

    file_list = event['file_list']
    for file_path in file_list:
        if prefix:
            key = "{}/{}".format(prefix, file_path)
        else:
            key = file_path

        print("check key={}".format(key))

        key_exist = False
        err_msg = ''
        if key.endswith("/"):
            if len(list_s3_by_prefix(bucket, key)) > 0:
                key_exist = True
            else:
                err_msg = "no file found in " + key
        elif s3_key_exists(bucket, key):
            key_exist = True
        else:
            err_msg = 'key doest exist'

        if not key_exist:
            raise FileNotFoundError("Pre-check failed, key:" + key + ", " + err_msg)

    print("Pre-check ok")
    return success_response("passed pre check")


def s3_base_name(key):
    return os.path.basename(key)


def success_response(message):
    return {
        "statusCode": 200,
        "UID": "".join(str(time.time()).split(".")),
        "headers": {
            "Content-Type": "application/json"
        },
        "body": message
    }


def error_response(message):
    return {
        "statusCode": 400,
        "UID": "".join(str(time.time()).split(".")),
        "headers": {
            "Content-Type": "application/json"
        },
        "body": message
    }
