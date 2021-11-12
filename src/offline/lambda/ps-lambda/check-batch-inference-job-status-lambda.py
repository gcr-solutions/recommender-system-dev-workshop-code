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
    batch_inference_job_arn = event['createBatchInferenceJob']['Payload']['batch_inference_job_arn']
    describe_batch_inference_job_response = personalize.describe_batch_inference_job(
        batchInferenceJobArn=batch_inference_job_arn
    )
    status = describe_batch_inference_job_response["batchInferenceJob"]["status"]
    print("Batch Inference Job Status: {}".format(status))

    return {
        "statusCode": 200,
        "batch_inference_job_arn": batch_inference_job_arn,
        "batch_inference_job_status": status
    }



