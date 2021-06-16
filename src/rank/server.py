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

app = FastAPI()

# Mandatory variables in envirnment
MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'RANK_PORT': 5400
    }

# Notice channel
recall_notice_to_rank='recall_notice_to_rank'
rank_notice_to_filter='rank_notice_to_filter'
sleep_interval = 10 #second

action_model_type = 'action-model'
embedding_type = 'embedding'
pickle_type = 'inverted-list'


def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target = f, args = args, kwargs = kwargs)
        thr.start()
    return wrapper

@app.get('/rank/status', tags=["monitoring"])
def status():
    logging.info('Collecting status information from server & plugin...')
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.RankStub(channel)
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

def check_plugin_status():
    logging.info('check plugin status')
    channel = grpc.insecure_channel('localhost:50051')
    stub = service_pb2_grpc.RankStub(channel)
    response = stub.Status(service_pb2.google_dot_protobuf_dot_empty__pb2.Empty())
    if response.code == 0:
        logging.info('plugin startup succeed')
        return True
    else:
        logging.info('plugin startup failed')
        return False

@xasync
def poll_recall_notice_to_rank():
    logging.info('poll_recall_notice_to_rank start')
    while True:
        try:
            message_redis = rCache.lpop_data_from_list(recall_notice_to_rank)
            if message_redis:
                logging.info('get message {} from {}'.format(message_redis, recall_notice_to_rank))
                message = json.loads(message_redis, encoding='utf-8')
                user_id = message['user_id']
                recall_result = message['recall_result']
                logging.info('start rank_process in poll_recall_notice_to_rank')
                logging.info('user_id {}'.format(user_id))
                logging.info('recall_result {}'.format(recall_result))

                reqDicts = any_pb2.Any()
                reqDicts.value = json.dumps({
                    'user_id': user_id,
                    'recall_result': recall_result
                }).encode('utf-8')

                rankProcessRequest = service_pb2.RankProcessRequest(apiVersion='v1', metadata='Rank', type='RankResult')
                rankProcessRequest.dicts.Pack(reqDicts)
                channel = grpc.insecure_channel('localhost:50051')
                stub = service_pb2_grpc.RankStub(channel)
                response = stub.RankProcess(rankProcessRequest)

                results = any_pb2.Any()
                response.results.Unpack(results)

                presults = json.loads(results.value.decode('utf-8'))
                logging.info('rank result: {}'.format(presults))

                if response.code == 0:
                    rCache.rpush_data_into_list(rank_notice_to_filter, json.dumps({
                        'user_id': user_id,
                        'recall_result': recall_result,
                        'rank_result': presults
                    }).encode('utf-8'))
            else:    
                time.sleep( sleep_interval )
        except Exception:
            localtime = time.asctime( time.localtime(time.time()))
            logging.info('Rank process error, time: {}'.format(localtime))                  

def read_stream_messages():
    logging.info('read_stream_messages start')
    read_action_model_message()
    read_embedding_message()
    read_pickle_message()

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
def read_embedding_message():
    logging.info('read_embedding_message start')
    # Read existed stream message
    stream_message = rCache.read_stream_message(embedding_type)
    if stream_message:
        logging.info("Handle existed stream embedding_type message")
        handle_stream_message(stream_message)
    while True:
        logging.info('wait for reading embedding_type message')
        try:
            stream_message = rCache.read_stream_message_block(embedding_type)
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
    stub = service_pb2_grpc.RankStub(channel)
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

    logging.info('rank service start')

    poll_recall_notice_to_rank()

    read_stream_messages()



if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    init()
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['RANK_PORT'])
    
   
