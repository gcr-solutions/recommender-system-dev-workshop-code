import os
import logging
import json
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import grpc 
from google.protobuf import any_pb2
import sys
import time
from threading import Thread
import redis
import boto3

import cache
import service_pb2
import service_pb2_grpc

s3client = None

class ProcessItem(BaseModel):
    user_id: str
    clicked_item_ids: list = []

app = FastAPI()

# Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'AWS_REGION': 'ap-northeast-1',
    'REDIS_HOST' : 'localhost',
    'REDIS_PORT' : 6379,

    'PORTRAIT_PORT': 5300
}

sleep_interval = 10 #second
pickle_type = 'inverted-list'
action_model_type = 'action-model'

def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target = f, args = args, kwargs = kwargs)
        thr.start()
    return wrapper

@app.get('/portrait/status', tags=["monitoring"])
def status():
    logging.info('Collecting status information from server & plugin...')
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.PortraitStub(channel)
    response = stub.Status(service_pb2.google_dot_protobuf_dot_empty__pb2.Empty())
    statusAny = any_pb2.Any()
    response.status.Unpack(statusAny)
    
    pStatus = json.loads(statusAny.value.decode('utf-8'))
    return {
        'env': MANDATORY_ENV_VARS,
        'redis': rCache.connection_status(),
        'plugin_status': pStatus
    }

@app.get('/ping', tags=["monitoring"])
def ping(): 
    logging.info('Processing default request')
    return {
        "result": "pong"
    }

@app.get('/portrait/userid/{user_id}', tags=["portrait"])
async def get_portrait(user_id: str):
    logging.info('Searching %s - user portrait from cache ...', user_id)

    # Get data from plugin service
    gPortraitRequest = service_pb2.GetPortraitRequest(apiVersion='v1', 
        metadata='Portrait', type='GetPortrait', userId=user_id)
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.PortraitStub(channel)
    response = stub.GetPortrait(gPortraitRequest)

    results = any_pb2.Any()
    response.results.Unpack(results)

    results = any_pb2.Any()
    response.results.Unpack(results)
    resultJson = json.loads(results.value, encoding='utf-8') 

    return {
        'code': response.code,
        'description': response.description,
        'results': resultJson
    }

@app.post('/portrait/process', tags=["portrait_to_plugin"])
def update_portrait(processItem: ProcessItem):
    logging.info('Start update_portrait() ...')
    user_id = processItem.user_id
    clicked_item_ids = processItem.clicked_item_ids
    logging.info('user_id -> %s', user_id)
    logging.info('clicked_item_ids -> %s', clicked_item_ids)
    reqDicts = any_pb2.Any()
    reqDicts.value = json.dumps({
        'user_id': user_id,
        'clicked_item_ids': clicked_item_ids
    }).encode('utf-8')

    logging.info('Invoke plugin to update portrait...')
    updateRequest = service_pb2.UpdatePortraitRequest(apiVersion='v1',
        metadata='Portrait', type='UpdatePortrait')
    updateRequest.dicts.Pack(reqDicts)
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.PortraitStub(channel)
    response = stub.UpdatePortrait(updateRequest)

    results = any_pb2.Any()
    response.results.Unpack(results)
    resultJson = json.loads(results.value, encoding='utf-8') 

    return {
        'code': response.code,
        'description': response.description,
        'results': resultJson
    }

def read_stream_messages():
    logging.info('read_stream_messages start')
    read_pickle_message()
    read_action_model_message()

@xasync
def read_action_model_message():
    logging.info('read_action_model_message start')
    # Read existed stream message
    stream_message = rCache.read_stream_message(action_model_type)
    if stream_message:
        logging.info("Handle existed stream action_model_type message")
        handle_stream_message(stream_message)
    while True:
        logging.info('wait for reading action_model_type message')
        try:
            stream_message = rCache.read_stream_message_block(action_model_type)
            if stream_message:
                handle_stream_message(stream_message)
        except redis.ConnectionError:
            localtime = time.asctime( time.localtime(time.time()))
            logging.info('get ConnectionError, time: {}'.format(localtime))                 
        time.sleep( sleep_interval )
@xasync
def read_pickle_message():
    logging.info('read_pickle_message start')       
    # Read existed stream message
    stream_message = rCache.read_stream_message(pickle_type)
    if stream_message:
        logging.info("Handle existed stream pickle_type message")
        handle_stream_message(stream_message)
    while True:
        logging.info('wait for reading pickle_type message')
        localtime = time.asctime( time.localtime(time.time()))
        logging.info('start read stream: time: {}'.format(localtime))
        try:
            stream_message = rCache.read_stream_message_block(pickle_type)
            if stream_message:
                handle_stream_message(stream_message)
        except redis.ConnectionError:
            localtime = time.asctime( time.localtime(time.time()))
            logging.info('get ConnectionError, time: {}'.format(localtime))
        time.sleep( sleep_interval )                

def handle_stream_message(stream_message):
    logging.info('get stream message from {}'.format(stream_message))
    file_type, file_path, file_list = parse_stream_message(stream_message)
    logging.info('start reload data process in handle_stream_message')
    logging.info('file_type {}'.format(file_type))
    logging.info('file_path {}'.format(file_path))
    logging.info('file_list {}'.format(file_list))

    reqDicts = any_pb2.Any()
    reqDicts.value = json.dumps({
        'file_type': file_type,
        'file_list': file_list
    }).encode('utf-8')

    reloadRequest = service_pb2.ReloadRequest()
    reloadRequest.dicts.Pack(reqDicts)
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.PortraitStub(channel)
    response = stub.Reload(reloadRequest)
    if response.code == 0:
        logging.info('reload plugin succeeded')
    else:
        logging.info('reload plugin failed, description: {}'.format(response.description))

def parse_stream_message(stream_message):
    for stream_name, message in stream_message:
        for message_id, value in message:
            decode_value = convert(value)
            file_type = decode_value['file_type']
            file_path = decode_value['file_path']
            file_list = decode_value['file_list']
            return file_type, file_path, file_list

# convert stream data to str
def convert(data):
    if isinstance(data, bytes):
        return data.decode('ascii')
    elif isinstance(data, dict):
        return dict(map(convert, data.items()))
    elif isinstance(data, tuple):
        return map(convert, data)
    else:
        return data

def check_plugin_status():
    logging.info('check plugin status')
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.PortraitStub(channel)
    response = stub.Status(service_pb2.google_dot_protobuf_dot_empty__pb2.Empty())
    if response.code == 0:
        logging.info('plugin startup succeed')
        return True
    else:
        logging.info('plugin startup failed')
        return False

def wait_for_plugin_service():
    while True:
        if check_plugin_status():
            return
        else:
            logging.info('wait for plugin startup')
            time.sleep( sleep_interval )        

def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var]=os.environ.get(var)

    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    logging.info("aws_region={}".format(aws_region))
    boto3.setup_default_session(region_name=MANDATORY_ENV_VARS['AWS_REGION'])
    global s3client
    s3client = boto3.client('s3')
    logging.info(json.dumps(s3client.list_buckets(), default=str))

    # Initial redis connection
    global rCache
    rCache = cache.RedisCache(host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])

    logging.info('redis status is {}'.format(rCache.connection_status()))

    wait_for_plugin_service()
    logging.info('portrait start!')
    read_stream_messages() 

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    init()
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['PORTRAIT_PORT'])
    
   
