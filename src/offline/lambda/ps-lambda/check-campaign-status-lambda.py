import json
import os
import boto3

print('Loading function')


def init():
    print('init() enter')
    my_config = json.loads(os.environ['botoConfig'])
    from botocore import config
    config = config.Config(**my_config)

    global personalize
    personalize = boto3.client('personalize', config=config)


def lambda_handler(event, context):
    init()
    try:
        print("Received event: " + json.dumps(event, indent=2))
        return do_handler(event, context)
    except Exception as e:
        print(e)
        raise e


def do_handler(event, context):
    campaign_arn = event['updateCampaign']['Payload']['campaign_arn']
    describe_campaign_response = personalize.describe_campaign(
        campaignArn=campaign_arn
    )
    status = describe_campaign_response["campaign"]["status"]
    print("Campaign Status: {}".format(status))

    return {
        "statusCode": 200,
        "campaign_status": status,
        "campaign_arn": campaign_arn
    }


