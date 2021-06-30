import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import os
import logging
import json
from google.protobuf import any_pb2
import grpc
import time
from threading import Thread
import sys
import redis

import cache
import service_pb2
import service_pb2_grpc
import datetime

app = FastAPI()

# Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'FILTER_PORT': 5200
    }

# Notice channel
rank_notice_to_filter='rank_notice_to_filter'
sleep_interval = 10 #second
pickle_type = 'inverted-list'

def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target = f, args = args, kwargs = kwargs)
        thr.start()
    return wrapper

@app.get('/filter/status', tags=["monitoring"])
def status():
    logging.info('Collecting status information from server & plugin...')
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.FilterStub(channel)
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
    logging.info('Processing default request...')
    return { 'result': 'ping' }

@app.get('/filter/get_recommend_data', tags=["filter_to_plugin"])
def get_recommend_data(userId: str, recommendType: str):
    logging.info('user_id -> %s', userId)
    logging.info('recommend_type -> %s', recommendType)
    
    logging.info('start get_recommend_data')

    request = any_pb2.Any()
    request.value = json.dumps({
        'user_id': userId,
        'recommend_type': recommendType
    }).encode('utf-8') 

    logging.info('Invoke plugin to get recommend data...')
    
    print("---------time before trigger getFilterData:")
    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))

    getFilterDataRequest = service_pb2.GetFilterDataRequest(apiVersion='v1', metadata='Filter', type='RecommendResult')
    getFilterDataRequest.requestBody.Pack(request)
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.FilterStub(channel)
    response = stub.GetFilterData(getFilterDataRequest)


    print("---------time after trigger getFilterData:")
    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
    
    
    
    results = any_pb2.Any()
    response.results.Unpack(results)
    resultJson = json.loads(results.value, encoding='utf-8')   

    print("---------time finish filter:")
    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
    
    if response.code == 0:
        return {
            'code': response.code,
            'description': response.description,
            'data': resultJson['data']
        }
    else:
        return {
            'code': -1,
            'description': 'failed to get recommend data',
            'data': ''
        }


@xasync
def poll_rank_notice_to_filter():
    logging.info('poll_rank_notice_to_filter start')
    while True:
        try:        
            message_redis = rCache.lpop_data_from_list(rank_notice_to_filter)
            if message_redis:
           #     logging.info('get message {} from {}'.format(message_redis, rank_notice_to_filter))
                message = json.loads(message_redis, encoding='utf-8')
                user_id = message['user_id']
                rank_result = message['rank_result']
                recall_result = message['recall_result']
                logging.info('start filter_process in poll_rank_notice_to_filter')
                logging.info('user_id {}'.format(user_id))
       #         logging.info('rank_result {}'.format(rank_result))
       #        logging.info('recall_result {}'.format(recall_result))

                reqDicts = any_pb2.Any()
                reqDicts.value = json.dumps({
                    'user_id': user_id,
                    'rank_result': rank_result,
                    'recall_result': recall_result
                }).encode('utf-8')

                filterProcessRequest = service_pb2.FilterProcessRequest(apiVersion='v1', metadata='Filter', type='FilterResult')
                filterProcessRequest.dicts.Pack(reqDicts)
                channel = grpc.insecure_channel('localhost:50051')
                stub = service_pb2_grpc.FilterStub(channel)
                response = stub.FilterProcess(filterProcessRequest)

                results = any_pb2.Any()
                response.results.Unpack(results)

                if response.code==0:
                    logging.info("filter process succeed, user_id {}".format(user_id))
                else:
                    logging.info("filter process failed, user_id {}, description {}".format(user_id, response.description))
            else:    
                time.sleep( sleep_interval ) 
        except Exception:
            localtime = time.asctime( time.localtime(time.time()))
            logging.info('Filter process error, time: {}'.format(localtime))                

def read_stream_messages():
    logging.info('read_stream_messages start')
    read_pickle_message()

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
#    logging.info('file_list {}'.format(file_list))

    reqDicts = any_pb2.Any()
    reqDicts.value = json.dumps({
        'file_type': file_type,
        'file_list': file_list
    }).encode('utf-8')

    reloadRequest = service_pb2.ReloadRequest()
    reloadRequest.dicts.Pack(reqDicts)
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.FilterStub(channel)
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
    stub = service_pb2_grpc.FilterStub(channel)
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

    # Initial redis connection
    global rCache
    rCache = cache.RedisCache(host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])

    logging.info('redis status is {}'.format(rCache.connection_status()))

    wait_for_plugin_service()

    logging.info('filter service start')
    poll_rank_notice_to_filter()

    read_stream_messages()




if __name__ == "__main__":

    print('server start')
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    init()
    
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['FILTER_PORT'])
    
   
