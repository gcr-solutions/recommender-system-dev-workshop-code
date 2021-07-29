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
    personalize = boto3.client('personalize', config=config)
    personalize_runtime = boto3.client('personalize-runtime', config=config)
    personalize_events = boto3.client(service_name='personalize-events', config=config)


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

    dataset_group_name = event['datasetGroupName']
    solution_name = event['solutionName']
    training_mode = event['trainingMode']

    dataset_group_arn = get_dataset_group_arn(dataset_group_name)
    print("dataset_group_arn:{}".format(dataset_group_arn))

    solution_arn = get_solution_arn(dataset_group_arn, solution_name)
    print("solution_arn:{}".format(solution_arn))

    solution_version_arn = update_solution_version(solution_arn, training_mode)
    print("solution_version_arn:{}".format(solution_arn))

    max_time = time.time() + 3 * 60 * 60  # 3 hours
    while time.time() < max_time:
        describe_solution_version_response = personalize.describe_solution_version(
            solutionVersionArn=solution_version_arn
        )
        status = describe_solution_version_response["solutionVersion"]["status"]
        print("SolutionVersion: {}".format(status))

        if status == "ACTIVE":
            return success_response("Update Solution Version Success!")
        elif status == "CREATE FAILED":
            return error_response("Update Solution Version Failed!")
        else:
            time.sleep(60)

    return error_response("DatasetImportJob Create exceed max time")


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


def update_solution_version(solution_arn, training_mode):
    response = personalize.create_solution_version(
        solutionArn=solution_arn,
        trainingMode=training_mode
    )
    return response["solutionVersionArn"]


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
