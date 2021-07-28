import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

import boto3
import requests
import uvicorn as uvicorn
from fastapi import FastAPI, Header, HTTPException, APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse
import service_pb2
import service_pb2_grpc
from google.protobuf import any_pb2
import grpc

app = FastAPI()
api_router = APIRouter()

s3client = boto3.client('s3')

step_funcs = None
account_id = ''

MANDATORY_ENV_VARS = {
    # 'REDIS_HOST': 'localhost',
    # 'REDIS_PORT': 6379,
    'EVENT_PORT': '5100',
    'PORTRAIT_HOST': 'portrait',
    'PORTRAIT_PORT': '5300',
    'RECALL_HOST': 'recall',
    'RECALL_PORT': '5500',
    'AWS_REGION': 'ap-southeast-1',
    'S3_BUCKET': 'aws-gcr-rs-sol-demo-ap-southeast-1-522244679887',
    'S3_PREFIX': 'sample-data',
    'POD_NAMESPACE': 'default',
    'TEST': 'False',
    'USE_PERSONALIZE_PLUGIN': 'False',
    'PERSONALIZE_RECIPE': 'user-personalize'
}


async def log_json(request: Request):
    try:
        logging.info("log request JSON: {}".format(await request.json()))
    except Exception:
        pass


class RSHTTPException(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code, message)


class RSAWSServiceException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


@app.exception_handler(HTTPException)
async def rs_exception_handler(request, rs_exec: HTTPException):
    return JSONResponse(
        status_code=rs_exec.status_code,
        content={
            "message": rs_exec.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc):
    print("exception_handler error >>> {}".format(exc))
    return JSONResponse(
        status_code=405,
        content={
            "message": str(exc)
        }
    )


@app.exception_handler(RSAWSServiceException)
async def rs_exception_handler(request: Request, rs_exc: RSAWSServiceException):
    return JSONResponse(
        status_code=400,
        content={
            "message": str(rs_exc)
        }
    )


def send_post_request(url, data):
    logging.info("send POST request to {}".format(url))
    logging.info("data: {}".format(data))
    if MANDATORY_ENV_VARS['TEST'] == 'True':
        return "[TEST] sent data to {}".format(url)

    headers = {'Content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    logging.info("status_code: {}".format(r.status_code))

    if r.status_code == 200:
        return "OK"
    else:
        if len(r.text) > 100:
            logging.error(r.text[100:300])
        else:
            logging.error(r.text)
        raise RSHTTPException(status_code=r.status_code,
                              message="error POST request {}".format(url))


def get_data_request(url, func=None):
    logging.info("GET request from :" + url)
    if MANDATORY_ENV_VARS['TEST'] == 'True':
        return {
            "test": "data from {}".format(url)
        }

    r = requests.get(url)
    logging.info("get response status_code:{}".format(r.status_code))
    if r.status_code == 200:
        if func:
            return func(r.json())
        else:
            return r.json()['data']
    else:
        if len(r.text) > 100:
            logging.error(r.text[100:300])
        else:
            logging.error(r.text)
        raise RSHTTPException(status_code=r.status_code,
                              message="error GET request {}".format(url))


class Item(BaseModel):
    id: str
    # subtype: str


class ClickedItem(BaseModel):
    clicked_item: Item


class ClickedItemList(BaseModel):
    clicked_item_list: List[Item]


class Metadata(BaseModel):
    type: str


class PortraitResponse(BaseModel):
    version: int = 1
    metadata: Metadata
    content: Dict[str, Any]


class TrainRequest(BaseModel):
    change_type: str


class SimpleResponse(BaseModel):
    version: int = 1
    metadata: Metadata
    message: str


class StateMachineStatus(BaseModel):
    # 'RUNNING'|'SUCCEEDED'|'FAILED'|'TIMED_OUT'|'ABORTED',
    status: Optional[str]
    startDate: datetime
    stopDate: Optional[datetime]


class StateMachineStatusResponse(BaseModel):
    version: int = 1
    metadata: Metadata
    status: StateMachineStatus
    detailUrl: str
    executionArn: str

class UserEntity(BaseModel):
    user_id: str
    user_sex: str

def gen_simple_response(message):
    res = SimpleResponse(
        message=message, metadata=Metadata(type='SimpleResponse'))
    return res


@app.get('/ping', tags=["monitoring"])
def ping():
    logging.info('Processing default request...')
    return {'result': 'ping'}


@api_router.get('/api/v1/event/portrait/{user_id}', response_model=PortraitResponse, tags=["event"])
def portrait_get(user_id: str, regionId=Header("1")):
    host = MANDATORY_ENV_VARS['PORTRAIT_HOST']
    port = MANDATORY_ENV_VARS['PORTRAIT_PORT']
    get_portrait_svc_url = "http://{}:{}/portrait/userid/{}".format(
        host, port, user_id)
    result_json = get_data_request(
        get_portrait_svc_url, lambda data: data['results'])
    return PortraitResponse(content=result_json, metadata=Metadata(type='PortraitResponse'))


@api_router.post('/api/v1/event/portrait/{user_id}', response_model=SimpleResponse, tags=["event"])
def portrait_post(user_id: str, clickItem: ClickedItem):
    host = MANDATORY_ENV_VARS['PORTRAIT_HOST']
    port = MANDATORY_ENV_VARS['PORTRAIT_PORT']
    portrait_svc_url = "http://{}:{}/portrait/process".format(host, port)
    data = {
        'user_id': user_id,
        'clicked_item_ids': [clickItem.clicked_item.id]
    }
    message = send_post_request(portrait_svc_url, data)
    res = gen_simple_response(message)
    return res


@api_router.post('/api/v1/event/recall/{user_id}', response_model=SimpleResponse, tags=["event"])
def recall_post(user_id: str, clickItemList: ClickedItemList):
    host = MANDATORY_ENV_VARS['RECALL_HOST']
    port = MANDATORY_ENV_VARS['RECALL_PORT']
    recall_svc_url = "http://{}:{}/recall/process".format(host, port)
    data = {
        'user_id': user_id,
        'clicked_item_ids': [item.id for item in clickItemList.clicked_item_list]
    }

    if MANDATORY_ENV_VARS['USE_PERSONALIZE_PLUGIN'] == "True":
        request = any_pb2.Any()
        request.value = json.dumps(data).encode('utf-8')
        logging.info('Invoke personalize plugin to trigger event tracker...')
        eventTrackerRequest = service_pb2.EventTrackerRequest(apiVersion='v1', metadata='Event',
                                                                      type='EventTracker')
        eventTrackerRequest.requestBody.Pack(request)
        channel = grpc.insecure_channel('localhost:50051')
        stub = service_pb2_grpc.EventStub(channel)
        response = stub.EventTracker(eventTrackerRequest)

        if response.code == 0:
            logging.info("----------event tracker from personalize plugin successful.")
            message = response.description
        else:
            logging.info("----------event tracker from personalize plugin failed.")
            message = "event tracker from personalize plugin failed."
    else:
        message = send_post_request(recall_svc_url, data)

    res = gen_simple_response(message)
    return res


@api_router.post('/api/v1/event/start_train', response_model=StateMachineStatusResponse, tags=["event"])
def start_train_post(trainReq: TrainRequest):
    if trainReq.change_type not in ['MODEL', 'CONTENT', 'ACTION']:
        raise HTTPException(status_code=405, detail="invalid change_type")

    # if MANDATORY_ENV_VARS['USE_PERSONALIZE_PLUGIN'] == "True":

    res = start_step_funcs(trainReq)
    return res


@api_router.post('/api/v1/event/start_update', response_model=StateMachineStatusResponse, tags=["event"])
def start_update_post(trainReq: TrainRequest):
    if trainReq.change_type not in ['MODEL', 'CONTENT', 'ACTION']:
        raise HTTPException(status_code=405, detail="invalid change_type")
    res = start_step_funcs(trainReq)
    return res


@api_router.get('/api/v1/event/offline_status/{exec_arn}', response_model=StateMachineStatusResponse, tags=["event"])
def offline_status_get(exec_arn: str):
    logging.info("stepfuncs_exec_status_get: exec_arn='{}'".format(exec_arn))
    res = step_funcs.describe_execution(
        executionArn=exec_arn
    )
    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    aws_console_url = f"https://{aws_region}.console.aws.amazon.com/states/home?region={aws_region}" \
                      f"#/executions/details/{exec_arn}"
    res = StateMachineStatusResponse(metadata=Metadata(type='StateMachineStatusResponse'),
                                     detailUrl=aws_console_url,
                                     executionArn=exec_arn,
                                     status=StateMachineStatus(
                                         status=res.get('status', None),
                                         startDate=res['startDate'],
                                         stopDate=res.get('stopDate', None))
                                     )
    return res


@api_router.post('/api/v1/event/add_user/{user_id}', response_model=SimpleResponse, tags=["event"])
def add_new_user(userEntity: UserEntity):
    logging.info("Add new user to AWS Personalize Service...")
    user_id = userEntity.user_id
    user_sex = userEntity.user_sex
    logging.info("New User Id:{}, Sex:{}".format(user_id, user_sex))

    request = any_pb2.Any()
    request.value = json.dumps({
        'userId': user_id,
        'gender': user_sex
    }).encode('utf-8')
    logging.info('Invoke personalize plugin to add new user...')
    addNewUserRequest = service_pb2.AddNewUserRequest(apiVersion='v1',metadata='Event',
                                                      type='AddNewUser')
    addNewUserRequest.requestBody.Pack(request)
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.EventStub(channel)
    response = stub.AddNewUser(addNewUserRequest)

    if response.code == 0:
        logging.info("add user to AWS Personalize Service successful.")
        message = response.description
    else:
        logging.info("add user to AWS Personalize Service failed.")
        message = "add user to AWS Personalize Service failed."

    return gen_simple_response(message)


def start_step_funcs(trainReq):
    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    step_funcs_name = get_step_funcs_name()
    bucket = MANDATORY_ENV_VARS['S3_BUCKET']
    key_prefix = MANDATORY_ENV_VARS['S3_PREFIX']

    stateMachineArn = f"arn:aws:states:{aws_region}:{account_id}:stateMachine:{step_funcs_name}"
    logging.info("start_step_funcs: {}, trainReq={}".format(
        stateMachineArn, trainReq))

    try:
        res = step_funcs.start_execution(
            stateMachineArn=stateMachineArn,
            name="{}-{}".format(trainReq.change_type[0].lower(), uuid.uuid1()),
            input=json.dumps({
                'change_type': trainReq.change_type,
                'Bucket': bucket,
                'S3Prefix': key_prefix
            })
        )
    except Exception as e:
        logging.error(repr(e))
        raise RSAWSServiceException(repr(e))

    exec_arn = res['executionArn']
    logging.info("exec_arn: {}".format(exec_arn))

    aws_console_url = f"https://{aws_region}.console.aws.amazon.com/states/home?region={aws_region}" \
                      f"#/executions/details/{exec_arn}"

    res = StateMachineStatusResponse(metadata=Metadata(type='StateMachineStatusResponse'),
                                     detailUrl=aws_console_url,
                                     executionArn=exec_arn,
                                     status=StateMachineStatus(
                                         status=None,
                                         startDate=res['startDate'],
                                         stopDate=None)
                                     )
    return res


app.include_router(api_router, dependencies=[Depends(log_json)])


def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.warning("Mandatory variable {%s} is not set, using default value {%s}.", var,
                            MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = str(os.environ.get(var))
        aws_region = MANDATORY_ENV_VARS['AWS_REGION']
        global step_funcs
        step_funcs = boto3.client('stepfunctions', aws_region)
        global account_id
        account_id = boto3.client(
            'sts', aws_region).get_caller_identity()['Account']


def get_step_funcs_name():
    namespace = MANDATORY_ENV_VARS['POD_NAMESPACE']
    known_mappings = {
        'rs-news-dev-ns': 'rs-dev-News-OverallStepFunc',
        'rs-movie-dev-ns': 'rs-dev-Movie-OverallStepFunc',
        'rs-news-demo-ns': 'rs-demo-News-OverallStepFunc',
        'rs-movie-demo-ns': 'rs-demo-Movie-OverallStepFunc',
        'rs-beta': 'rsdemo-News-OverallStepFunc'
    }
    step_funcs_name = known_mappings.get(namespace, 'rsdemo-News-OverallStepFunc')

    # change for dev-workshop
    s3bucket = MANDATORY_ENV_VARS['S3_BUCKET']
    if '-dev-workshop-' in s3bucket and namespace == 'rs-news-dev-ns':
        step_funcs_name = 'rs-dev-workshop-News-OverallStepFunc'

    logging.info("get_step_funcs_name return: namespace: {}, step funcs name: {}".format(namespace, step_funcs_name))
    return step_funcs_name


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    logging.info(json.dumps(s3client.list_buckets(), default=str))
    # aws_region = boto3.Session().region_name
    # logging.info("boto3.Session aws_region: {}".format(aws_region))

    init()
    logging.info(MANDATORY_ENV_VARS)
    uvicorn.run(app, host="0.0.0.0", port=int(
        MANDATORY_ENV_VARS['EVENT_PORT']))
