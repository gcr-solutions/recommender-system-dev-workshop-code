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

    if solution_name == "userPersonalizeSolutionNew":
        campaign_name = "gcr-rs-dev-workshop-news-ranking-campaign"
    elif solution_name == "userPersonalizeSolutionNew":
        campaign_name = "gcr-rs-dev-workshop-news-UserPersonalize-campaign"
    else:
        return error_response("invalid solution name")

    campaign_arn = get_campaign_arn(solution_arn, campaign_name)
    print("campaign_arn:{}".format(campaign_arn))

    campaign_arn = update_campaign(campaign_arn, solution_version_arn)

    max_time = time.time() + 3 * 60 * 60  # 3 hours
    while time.time() < max_time:
        describe_campaign_response = personalize.describe_campaign(
            campaignArn=campaign_arn
        )
        status = describe_campaign_response["campaign"]["status"]
        print("Campaign: {}".format(status))

        if status == "ACTIVE":
            return success_response("Update Campaign Success!")
        elif status == "CREATE FAILED":
            return error_response("Update Campaign Failed!")
        else:
            time.sleep(60)

    return error_response("Update Campaign exceed max time")


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


def get_campaign_arn(solution_arn, campaign_name):
    response = personalize.list_campaigns(
        solutionArn=solution_arn
    )
    for campaign in response["campaigns"]:
        if campaign["name"] == campaign_name:
            return campaign["campaignArn"]


def update_campaign(campaign_arn, solution_version_arn):
    response = personalize.update_campaign(
        campaignArn=campaign_arn,
        solutionVersionArn=solution_version_arn,
        minProvisionedTPS=10
    )
    return response['campaignArn']


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
