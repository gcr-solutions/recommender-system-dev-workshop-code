import logging
import math
import os
from threading import Thread
from typing import List
from urllib.request import Request

import requests
import uvicorn as uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic.main import BaseModel
from starlette.responses import JSONResponse
import redis
import cache
import time
import service_pb2
import service_pb2_grpc
from google.protobuf import any_pb2
import grpc
import json


app = FastAPI()
json_type = 'ps-result'
pickle_type = 'inverted-list'
sleep_interval = 10  # second

MANDATORY_ENV_VARS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'RETRIEVE_HOST': 'retrieve',
    'RETRIEVE_PORT': '5600',
    'FILTER_HOST': 'filter',
    'FILTER_PORT': '5200',
    'TEST': 'False',
    'METHOD': 'customize'
}


def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


class RSHTTPException(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code, message)


@app.exception_handler(HTTPException)
async def rs_exception_handler(request: Request, rs_exec: HTTPException):
    return JSONResponse(
        status_code=rs_exec.status_code,
        content={
            "message": rs_exec.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=405,
        content={
            "message": str(exc)
        }
    )


def get_data_request(url, get_data_func=None):
    logging.info("GET request from :" + url)
    if MANDATORY_ENV_VARS['TEST'] == 'True':
        return [
            {
                "id": "1111",
                "tag": "coldstart test",
                "type": "1"
            },
            {
                "id": "1112",
                "tag": "coldstart test",
                "type": "1"
            }
        ]

    r = requests.get(url)
    logging.info("get response status_code:{}".format(r.status_code))
    if r.status_code == 200:
        logging.info(r.json())
        if get_data_func is not None:
            return get_data_func(r.json())
        else:
            return r.json()['data']
    else:
        if len(r.text) > 100:
            logging.error(r.text[100:300])
        else:
            logging.error(r.text)
        raise RSHTTPException(status_code=r.status_code, message="error GET request {}".format(url))


class Metadata(BaseModel):
    type: str


class RSItem(BaseModel):
    id: str
    tags: List[str]
    description: str


class Pagination(BaseModel):
    curPage: int
    pageSize: int
    totalSize: int
    totalPage: int


class RecommendList(BaseModel):
    version: int = 1
    metadata: Metadata
    content: List[RSItem]
    pagination: Pagination


@app.get('/ping', tags=["monitoring"])
def ping():
    logging.info('Processing default request...')
    return {'result': 'ping'}


@app.get('/api/v1/retrieve/{user_id}', response_model=RecommendList, tags=["retrieve"])
def retrieve_get_v2(user_id: str, curPage: int = 0, pageSize: int = 20, regionId=Header("0"), recommendType: str = 'recommend'):
    logging.info("retrieve_get_v2() enter")
    item_list = get_recommend_data(user_id, recommendType)

    logging.info("retrieve_get_v2 item_list :{}".format(item_list))

    it_list = [RSItem(id=str(it['id']), description=str(it['description']), tags=str(it["tag"]).split(" ")) for it in item_list]
    # it_list_paged = it_list[curPage * pageSize: (curPage + 1) * pageSize]
    # total_page = math.ceil(len(it_list) / pageSize)

    # content = it_list_paged
    # pagination = Pagination(curPage=curPage, pageSize=pageSize,
    #                         totalSize=len(it_list),
    #                         totalPage=total_page)

    pagination = Pagination(curPage=curPage, pageSize=pageSize,
                            totalSize=len(it_list),
                            totalPage=1)

    rs_list = RecommendList(
        metadata=Metadata(type="RecommendList"),
        content=it_list,
        pagination=pagination
    )

    logging.info("rs_list: {}".format(rs_list))
    return rs_list

def get_recommend_data(userId: str, recommendType: str):
    logging.info('start get_recommend_data')
    logging.info('user_id -> %s', userId)
    logging.info('recommend_type -> %s', recommendType)

    if MANDATORY_ENV_VARS['TEST'] == 'True':
        return [
            {
                "id": "1111",
                "tag": "coldstart test",
                "type": "1"
            },
            {
                "id": "1112",
                "tag": "coldstart test",
                "type": "1"
            }
        ]

    request = any_pb2.Any()
    request.value = json.dumps({
        'user_id': userId,
        'recommend_type': recommendType
    }).encode('utf-8')

    logging.info('Invoke plugin to get recommend data...')
    if MANDATORY_ENV_VARS['METHOD'] == "ps-complete":
        getPsRecommendDataRequest = service_pb2.GetPsRecommendDataRequest(apiVersion='v1', metadata='Retrieve',
                                                                      type='PsRecommendResult')
        getPsRecommendDataRequest.requestBody.Pack(request)
        channel = grpc.insecure_channel('localhost:50051')
        stub = service_pb2_grpc.RetrieveStub(channel)
        response = stub.GetPsRecommendData(getPsRecommendDataRequest)
    else:
        getRecommendDataRequest = service_pb2.GetRecommendDataRequest(apiVersion='v1', metadata='Retrieve', type='RecommendResult')
        getRecommendDataRequest.requestBody.Pack(request)
        channel = grpc.insecure_channel('localhost:50051')
        stub = service_pb2_grpc.RetrieveStub(channel)
        response = stub.GetRecommendData(getRecommendDataRequest)

    results = any_pb2.Any()
    response.results.Unpack(results)
    resultJson = json.loads(results.value, encoding='utf-8')

    if response.code == 0:
        return resultJson['data']
    else:
        return {'data': ''}


# ## only for news
# @app.get('/api/v1/retrieve/{user_id}', response_model=RecommendList, tags=["retrieve"])
# def retrieve_get_v1(user_id: str, curPage: int = 0, pageSize: int = 20, regionId=Header("0")):
#     logging.info("retrieve_get_v1() enter")
#     host = MANDATORY_ENV_VARS['FILTER_HOST']
#     port = MANDATORY_ENV_VARS['FILTER_PORT']
#     content_dict = {}
#     pagenation_dict = {}
#
#     sub_types = ["recommend"]
#
#     for type in sub_types:
#         svc_url = "http://{}:{}/filter/get_recommend_data?userId={}&recommendType={}" \
#             .format(host, port, user_id, type)
#
#         logging.info("svc_url:{}".format(svc_url))
#         item_list = get_data_request(svc_url, lambda json_data: json_data['data'])
#
#         it_list = [RSItem(id=str(it['id']), tags=str(it["tag"]).split(" ")) for it in item_list]
#         it_list_paged = it_list[curPage * pageSize: (curPage + 1) * pageSize]
#         total_page = math.ceil(len(it_list) / pageSize)
#
#         content_dict[type] = it_list_paged
#         pagenation_dict[type] = Pagination(curPage=curPage, pageSize=pageSize,
#                                            totalSize=len(it_list),
#                                            totalPage=total_page)
#
#     rs_list = RecommendList(
#         metadata=Metadata(type="RecommendList", subtype=sub_types),
#         content=content_dict,
#         pagination=pagenation_dict
#     )
#
#     logging.info("rs_list: {}".format(rs_list))
#     return rs_list

@xasync
def read_pickle_message():
    logging.info('read_pickle_type_message start')
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


@xasync
def read_json_message():
    logging.info('read_json_type_message start')
    # Read existed stream message
    stream_message = rCache.read_stream_message(json_type)
    if stream_message:
        logging.info("Handle existed stream json_type message")
        handle_stream_message(stream_message)
    while True:
        logging.info('wait for reading json_type message')
        try:
            stream_message = rCache.read_stream_message_block(json_type)
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
    stub = service_pb2_grpc.RecallStub(channel)
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



def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = str(os.environ.get(var))
    global rCache
    rCache = cache.RedisCache(host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])
    logging.info('redis status is {}'.format(rCache.connection_status()))


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    init()
    uvicorn.run(app, host="0.0.0.0", port=int(MANDATORY_ENV_VARS['RETRIEVE_PORT']))
