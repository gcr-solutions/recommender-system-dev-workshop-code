import json
import os
import time
import boto3

print('Loading function')


def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)

    global personalize
    global personalize_runtime
    global personalize_events
    global sts
    personalize = boto3.client('personalize', config=config)
    personalize_runtime = boto3.client('personalize-runtime', config=config)
    personalize_events = boto3.client(service_name='personalize-events', config=config)
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

    bucket = event['bucket']
    s3_key_prefix = event['prefix']
    dataset_group_name = event['datasetGroupName']
    dataset_name = event['datasetName']

    dataset_group_arn = get_dataset_group_arn(dataset_group_name)
    print("dataset_group_arn:{}".format(dataset_group_arn))

    dataset_arn = get_dataset_arn(dataset_group_arn, dataset_name)
    print("dataset_arn:{}".format(dataset_arn))

    if dataset_name == "NewsUserDataset":
        file_path = "personalize_user.csv"
    elif dataset_name == "NewsItemDataset":
        file_path = "personalize_item.csv"
    elif dataset_name == "NewsInteractionDataset":
        file_path = "personalize_interactions.csv"
    else:
        return error_response("dataset name invalid!")

    get_caller_identity_response = sts.get_caller_identity()
    aws_account_id = get_caller_identity_response["Account"]
    print("aws_account_id:{}".format(aws_account_id))

    role_arn = "arn:aws:iam::{}:role/gcr-rs-{}-workshop-personalize-role".format(aws_account_id, stage)
    print("role_arn:{}".format(role_arn))

    create_dataset_import_job_response = personalize.create_dataset_import_job(
        jobName="dataset-import-job-{}".format(time.time()),
        datasetArn=dataset_arn,
        dataSource={
            "dataLocation": "s3://{}/{}/system/personalize-data/{}".format(bucket, s3_key_prefix, file_path)
        },
        roleArn=role_arn
    )
    dataset_import_job_arn = create_dataset_import_job_response['datasetImportJobArn']
    print("dataset_import_job_arn:{}".format(dataset_import_job_arn))

    # check status
    max_time = time.time() + 3 * 60 * 60
    while time.time() < max_time:
        describe_dataset_import_job_response = personalize.describe_dataset_import_job(
            datasetImportJobArn=dataset_import_job_arn
        )
        status = describe_dataset_import_job_response["datasetImportJob"]['status']
        print("DatasetImportJob: {}".format(status))

        if status == "ACTIVE":
            return success_response("DatasetImportJob Create Success")
        elif status == "CREATE FAILED":
            return error_response("DatasetImportJob Create failed")
        else:
            time.sleep(60)

    return error_response("DatasetImportJob Create exceed max time")


def get_dataset_group_arn(dataset_group_name):
    response = personalize.list_dataset_groups()
    for dataset_group in response["datasetGroups"]:
        if dataset_group["name"] == dataset_group_name:
            return dataset_group["datasetGroupArn"]


def get_dataset_arn(dataset_group_arn, dataset_name):
    response = personalize.list_datasets(
        datasetGroupArn=dataset_group_arn
    )
    for dataset in response["datasets"]:
        if dataset["name"] == dataset_name:
            return dataset["datasetArn"]


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
