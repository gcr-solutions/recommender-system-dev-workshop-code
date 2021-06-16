import datetime
import glob
import json
import os
import re

import boto3

print('Loading function')

s3_client = None
NOW = None


def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)
    global s3_client
    s3_client = boto3.client('s3', config=config)


'''
{
    "bucket": "bucket-a",
    "action": [{
            "type": "copy",
            "from": "key1",
            "to": "key2-{NOW}.txt",
            "add_timestamp": false,
            "filter": "*.csv"

        },
        {
            "type": "move",
            "from": "key1",
            "to": "key2",
            "add_timestamp": true
        },
        {
            "type": "delete",
            "key": "key1"
        }
    ]
}
'''


def lambda_handler(event, context):
    init()
    global NOW
    NOW = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    try:
        print("Received event: " + json.dumps(event, indent=2))
        return do_handler(event, context)
    except Exception as e:
        print(e)
        raise e


def s3_copy(from_bucket, to_bucket, from_key, to_key):
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
    print("copied {} to {}".format(from_key, to_key))


def s3_move(from_bucket, to_bucket, from_key, to_key):
    s3_copy(from_bucket, to_bucket, from_key, to_key)
    s3_client.delete_object(
        Bucket=from_bucket,
        Key=from_key,
    )
    print("moved {} to {}".format(from_key, to_key))


def s3_clean_dir(bucket, key_prefix, name_filter):
    for key in list_s3_by_prefix(bucket, key_prefix, name_filter):
        s3_client.delete_object(
            Bucket=bucket,
            Key=key,
        )


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


def match_filter(key, name_filter):
    if name_filter is None or name_filter == '' or name_filter == '*':
        return True

    name = s3_base_name(key).lower()
    if glob.fnmatch.fnmatch(name, name_filter):
        return True

    print("match_filter: ignore file {}, name_filter {}".format(key, name_filter))
    return False


def s3_copy_or_move_object(from_bucket, to_bucket, from_key, target_key, type_action):
    if type_action == "copy":
        s3_copy(from_bucket, to_bucket, from_key, target_key)
        return "copy s3://{}/{} s3://{}/{}".format(from_bucket, from_key, to_bucket, target_key)
    elif type_action == "move":
        s3_move(from_bucket, to_bucket, from_key, target_key)
        return "move s3://{}/{} s3://{}/{}".format(from_bucket, from_key, to_bucket, target_key)
    else:
        raise Exception('Unknown type_action:' + type_action)


def s3_copy_dir_to_dir(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp, name_filter):
    """ ignore file name start with '_' """
    print("s3_copy_dir_to_dir")
    ret_list = []
    for key in s3_list_key_prefix(from_bucket, from_key, name_filter):
        base_key = s3_base_name(key)
        if base_key.startswith("_"):
            continue
        target_key = "{}{}".format(to_key, base_key)
        if add_timestamp:
            target_key = target_key + "-" + NOW
        ret_list.append(s3_copy_or_move_object(from_bucket, to_bucket, key, target_key, type_action))
    return ret_list


def s3_copy_dir_to_object(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp, name_filter):
    """ ignore file name start with '_' """
    print("s3_copy_dir_to_object")
    ret_list = []
    for key in s3_list_key_prefix(from_bucket, from_key, name_filter):
        base_key = s3_base_name(key)
        if base_key.startswith("_"):
            print("ignore file {}".format(key))
            continue

        target_key = to_key
        if add_timestamp:
            target_key = target_key + "-" + NOW
        if "{NOW}" in to_key:
            target_key = target_key.replace('{NOW}', NOW)
        ret_list.append(s3_copy_or_move_object(from_bucket, to_bucket, key, target_key, type_action))
    return ret_list


def s3_copy_object_to_dir(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp):
    print("s3_copy_object_to_dir")
    ret_list = []
    target_key = "{}{}".format(to_key, s3_base_name(from_key))
    if add_timestamp:
        target_key = target_key + "-" + NOW
    ret_list.append(s3_copy_or_move_object(from_bucket, to_bucket, from_key, target_key, type_action))
    return ret_list


def s3_copy_object_to_object(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp):
    print("s3_copy_object_to_object")
    ret_list = []
    target_key = to_key
    if add_timestamp:
        target_key = target_key + "-" + NOW

    if "{NOW}" in to_key:
        target_key = target_key.replace('{NOW}', NOW)

    ret_list.append(s3_copy_or_move_object(from_bucket, to_bucket, from_key, target_key, type_action))
    return ret_list


def s3_delete_object(bucket, key):
    s3_client.delete_object(
        Bucket=bucket,
        Key=key,
    )


def process_copy_move_action(from_bucket, to_bucket, type_action, from_key, to_key, add_timestamp, name_filter):
    print("process_copy_move_action: \nfrom_bucket: {}, \nto_bucket: {} \ntype_action: {}, "
          "\nfrom_key: {}, \nto_key: {}, \nadd_timestamp: {}, "
          "\nname_filter: {} "
          .format(from_bucket, to_bucket, type_action, from_key, to_key, add_timestamp, name_filter))

    if from_key.endswith('/') and to_key.endswith('/'):
        return s3_copy_dir_to_dir(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp, name_filter)
    elif from_key.endswith('/'):
        return s3_copy_dir_to_object(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp, name_filter)
    elif to_key.endswith('/'):
        return s3_copy_object_to_dir(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp)
    else:
        return s3_copy_object_to_object(from_bucket, to_bucket, from_key, to_key, type_action, add_timestamp)


def process_delete_action(bucket, del_key, name_filter):
    print("process_delete_action: \nbucket: {}, \ndel_key: {}, \nname_filter: {}"
          .format(bucket, del_key, name_filter))
    ret_list = []
    if del_key.endswith("/"):
        for key in s3_list_key_prefix(bucket, del_key, name_filter):
            s3_delete_object(bucket, key)
            ret_list.append("delete {}".format(key))
    else:
        s3_delete_object(bucket, del_key)
        ret_list.append("delete {}".format(del_key))

    return ret_list


def do_handler(event, context):
    bucket = event['bucket']
    action_list = event['action']
    prefix = event.get("prefix", "")

    list_ret = []
    for action in action_list:
        type_action = action.get('type', 'copy')
        name_filter = None
        if 'filter' in action:
            name_filter = action['filter']

        if type_action == 'delete':
            bucket, input_key = parse_from_key(action['key'], bucket, prefix)
            list_ret.extend(process_delete_action(bucket, input_key, name_filter))
        else:
            from_bucket, from_key = parse_from_key(action['from'], bucket, prefix)
            to_bucket, to_key = parse_from_key(action['to'], bucket, prefix)

            add_timestamp = False
            if 'add_timestamp' in action:
                if str(action['add_timestamp']).lower() == 'true':
                    add_timestamp = True
            list_ret.extend(
                process_copy_move_action(from_bucket, to_bucket, type_action, from_key, to_key, add_timestamp,
                                         name_filter))
    return success_response(list_ret)


def parse_from_key(from_key, default_bucket, prefix):
    if from_key.startswith("s3://"):
        print("input is full s3 url: {}".format(from_key))
        regexp = re.compile(r"s3://([^/]+)/(.*)")
        result = regexp.search(from_key)
        if result is None:
            raise Exception("invalid s3 url {}".format(from_key))
        else:
            input_bucket = result.group(1)
            input_from_key = result.group(2)
            print("parse_from_key return: bucket: {}, from_key: {}".format(input_bucket, input_from_key))
            return input_bucket, input_from_key
    else:
        if prefix.endswith("/"):
            prefix = prefix[:-1]
        return default_bucket, "{}/{}".format(prefix, from_key)


def s3_base_name(key):
    return os.path.basename(key)


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
