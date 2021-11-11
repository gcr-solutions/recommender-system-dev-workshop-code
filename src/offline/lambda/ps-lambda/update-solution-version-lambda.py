import json
import os
import boto3

print('Loading function')

s3_client = None
personalize = None

def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)

    global personalize
    personalize = boto3.client('personalize', config=config)
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


def do_handler(event, context):
    bucket = event['bucket']
    s3_key_prefix = event['prefix']
    ps_config_json = get_ps_config(bucket, s3_key_prefix)
    dataset_group_name = ps_config_json['DatasetGroupName']
    solution_name = ps_config_json['SolutionName']
    training_mode = ps_config_json['TrainingMode']

    dataset_group_arn = get_dataset_group_arn(dataset_group_name)
    print("dataset_group_arn:{}".format(dataset_group_arn))

    solution_arn = get_solution_arn(dataset_group_arn, solution_name)
    print("solution_arn:{}".format(solution_arn))

    response = personalize.create_solution_version(
        solutionArn=solution_arn,
        trainingMode=training_mode
    )

    solution_version_arn = response["solutionVersionArn"]
    print("solution_version_arn:{}".format(solution_version_arn))

    return {
        "statusCode": 200,
        "solution_version_arn": solution_version_arn
    }


def get_solution_arn(dataset_group_arn, solution_name):
    response = personalize.list_solutions(
        datasetGroupArn=dataset_group_arn
    )
    for solution in response["solutions"]:
        if solution["name"] == solution_name:
            return solution["solutionArn"]


def get_dataset_group_arn(dataset_group_name):
    response = personalize.list_dataset_groups()
    for dataset_group in response["datasetGroups"]:
        if dataset_group["name"] == dataset_group_name:
            return dataset_group["datasetGroupArn"]


def get_ps_config(bucket, s3_key_prefix):
    KEY_NAME = s3_key_prefix + "/system/ps-config/ps_config.json"
    LOCAL_FILE_PATH = "/tmp/ps_config.json"

    print("ps_config.json doesn't exist in Local, Download ps_config.json from S3.")
    s3_client.download_file(bucket, KEY_NAME, LOCAL_FILE_PATH)
    input_file = open(LOCAL_FILE_PATH, 'rb')
    dict = json.load(input_file)
    input_file.close()
    return dict