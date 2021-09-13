import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import os
import logging
import json
import time
from threading import Thread
from multiprocessing import Process, Pool
from functools import partial
import boto3
import botocore
import sys

import cache

s3client = None

class LoadMessage(BaseModel):
    file_type: str
    file_path: str
    file_name: list = []


class LoadRequest(BaseModel):
    message: LoadMessage = None


app = FastAPI()

# Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'AWS_REGION': 'ap-northeast-1',
    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',
    'S3_BUCKET_DATA': 'aws-gcr-rs-sol-demo-ap-southeast-1-522244679887',
    "RECORDS_PATH": 'news-open/system/item-data/meta-data/',

    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'LOADER_PORT': 5000
}

item_records = 'item_records_dict'
action_model = 'model.tar.gz'


def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


@app.get('/loader/status', tags=["monitoring"])
def status():
    logging.info('Collecting status information from server & plugin...')
    return {
        'env': MANDATORY_ENV_VARS,
        'redis': rCache.connection_status()
    }


@app.get('/ping', tags=["monitoring"])
def ping():
    logging.info('Processing default request...')
    return {'result': 'ping'}


@app.post('/loader/notice', tags=["loader-service"])
def notice(loadRequest: LoadRequest):
    logging.info('Start loader->process()...')

    loader_message = loadRequest.message
    file_type = loader_message.file_type
    file_path = loader_message.file_path
    file_list = loader_message.file_name
    logging.info('file type:{}, file_path:{}, file_list:{}'.format(
        file_type, file_path, file_list))
    if not os.path.exists(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']):
        logging.info("the local path {} is not existed".format(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']))
        os.mkdir(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'])
    if file_type == 'inverted-list':
        for file in file_list:
            init_single_pickle_data(file_path, file)
    else:
        for file in file_list:
            if file_type == 'action-model':
                init_data_file(file_path, file)
            elif file_type == 'vector-index':
                init_data_file(file_path, file)
            elif file_type == 'embedding':
                init_data_file(file_path, file)
    time.sleep(10)
    notice_service_to_reload(
        file_type, MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'], file_list)

    return json.dumps({'result': 'success'}), 200, {'ContentType': 'application/json'}

def init_single_pickle_data(path, file):

    download_file_from_s3(MANDATORY_ENV_VARS['S3_BUCKET_DATA'], path, file, MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'])

def init_data_file(path, file):
    download_file_from_s3(MANDATORY_ENV_VARS['S3_BUCKET_DATA'], path, file, MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'])

def download_file_from_s3(bucket, path, file, dest_folder):
    logging.info('Download file - %s from s3://%s/%s ... ', file, bucket, path)

    # Using default session
    s3client = boto3.client('s3')
    try:
        s3client.download_file(bucket, path+file, dest_folder+file)
    except botocore.exceptions.ClientError as error:
        raise error
    except botocore.exceptions.ParamValidationError as error:
        raise ValueError(
            'The parameters you provided are incorrect: {}'.format(error))

    logging.info(
        'Download file - %s from s3://%s/%s ... was success', file, bucket, path)
    return dest_folder+file


def notice_service_to_reload(type, file_path, file_list):
    logging.info('type=%s, file_path=%s, file_list=%s',
                 type, file_path, file_list)
    data = {
        'file_type': type,
        'file_path': file_path,
        'file_list': str(file_list)
    }
    rCache.load_data_into_stream(type, data)


def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error(
                "Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)

    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    logging.info("aws_region={}".format(aws_region))
    boto3.setup_default_session(region_name=MANDATORY_ENV_VARS['AWS_REGION'])
    global s3client
    s3client = boto3.client('s3')
    logging.info(json.dumps(s3client.list_buckets(), default=str))

    # Initial redis connection
    global rCache
    rCache = cache.RedisCache(
        host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])

    logging.info('redis status is {}'.format(rCache.connection_status()))


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    init()
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['LOADER_PORT'])
