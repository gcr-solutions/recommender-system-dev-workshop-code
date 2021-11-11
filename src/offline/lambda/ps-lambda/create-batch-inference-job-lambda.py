import json
import os
import boto3
import time

print('Loading function')

s3_client = None
personalize = None
sts = None

def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)

    global personalize
    global sts
    global s3_client
    s3_client = boto3.client('s3', config=config)
    personalize = boto3.client('personalize', config=config)
    sts = boto3.client('sts', config=config)

def lambda_handler(event, context):
    init()
    try:
        print("Received event: " + json.dumps(event, indent=2))
        return do_handler(event, context)
    except Exception as e:
        print(e)
        raise e

stage = "dev"

def do_handler(event, context):
    global stage
    stage = os.environ.get('Stage', 'dev')
    region = os.environ.get('AWS_REGION')

    bucket = event['bucket']
    s3_key_prefix = event['prefix']
    ps_config_json = get_ps_config(bucket, s3_key_prefix)
    solution_version_arn = ps_config_json['SolutionVersionArn']

    get_caller_identity_response = sts.get_caller_identity()
    aws_account_id = get_caller_identity_response["Account"]
    print("aws_account_id:{}".format(aws_account_id))

    role_arn = "arn:aws:iam::{}:role/gcr-rs-personalize-role-{}".format(aws_account_id, region)
    print("role_arn:{}".format(role_arn))

    solution_name = ps_config_json['SolutionName']
    if solution_name == "UserPersonalizeSolution":
        file_name = "ps-complete-batch"
    elif solution_name == "RankingSolution":
        file_name = "ps-rank-batch"
    elif solution_name == "SimsSolution":
        file_name = "ps-sims-batch"
    else:
        raise AttributeError("Invalid Solution Name")

    response = personalize.create_batch_inference_job(
        solutionVersionArn=solution_version_arn,
        jobName="get-batch-recommend-job-{}".format(int(time.time())),
        roleArn=role_arn,
        jobInput={
            "s3DataSource": {
                "path": "s3://{}/{}/system/ps-ingest-data/batch-input/{}".format(bucket, s3_key_prefix, file_name)
            }
        },
        jobOutput={
            "s3DataDestination": {
                "path": "s3://{}/{}/feature/ps-recommend-list/".format(bucket, s3_key_prefix)
            }
        }
    )

    batch_inference_job_arn = response['batchInferenceJobArn']

    return {
        "statusCode": 200,
        "batch_inference_job_arn": batch_inference_job_arn
    }


def get_ps_config(bucket, s3_key_prefix):
    KEY_NAME = s3_key_prefix + "/system/ps-config/ps_config.json"
    LOCAL_FILE_PATH = "/tmp/ps_config.json"

    if not os.path.isfile(LOCAL_FILE_PATH):
        print("ps_config.json doesn't exist in Local, Download ps_config.json from S3.")
        s3_client.download_file(bucket, KEY_NAME, LOCAL_FILE_PATH)

    input_file = open(LOCAL_FILE_PATH, 'rb')
    dict = json.load(input_file)
    input_file.close()
    return dict



