import json
import os
import boto3

print('Loading function')

s3_client = None

def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)
    global s3_client
    s3_client = boto3.resource('s3', config=config)


def lambda_handler(event, context):
    init()
    try:
        print("Received event: " + json.dumps(event, indent=2))
        return do_handler(event, context)
    except Exception as e:
        print(e)
        raise e


def do_handler(event, context):
    bucket = event['bucket']
    s3_prefix = event['prefix']
    solution_version_arn = event['updateSolutionVersion']['Payload']['solution_version_arn']

    file_name = 'ps_config.json'
    file_key = '{}/system/ps-config/ps_config.json'.format(s3_prefix)
    object_str = s3_client.Object(bucket, file_key).get()['Body'].read().decode('utf-8')
    config = json.loads(object_str)

    config['SolutionVersionArn'] = solution_version_arn

    g = open('/tmp/config.json', 'w', encoding='utf8')
    g.write(json.dumps(config, indent=2))
    g.close()

    with open('/tmp/config.json', 'rb') as f:
        s3_client.Object(bucket, file_key).put(Body=f)

    return {
        "statusCode": 200
    }

