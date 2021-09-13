import logging
import math
import os
from typing import List
from urllib.request import Request
import boto3
import json

import requests
import uvicorn as uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic.main import BaseModel
from starlette.responses import JSONResponse

app = FastAPI()

MANDATORY_ENV_VARS = {
    'AWS_REGION': 'ap-northeast-1',
    # 'REDIS_HOST': 'localhost',
    # 'REDIS_PORT': 6379,
    'RETRIEVE_HOST': 'retrieve',
    'RETRIEVE_PORT': '5600',
    'FILTER_HOST': 'filter',
    'FILTER_PORT': '5200',
    'TEST': 'False'
}

s3client = None

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

    host = MANDATORY_ENV_VARS['FILTER_HOST']
    port = MANDATORY_ENV_VARS['FILTER_PORT']

    svc_url = "http://{}:{}/filter/get_recommend_data?userId={}&recommendType={}" \
        .format(host, port, user_id, recommendType)
    logging.info("svc_url:{}".format(svc_url))

    item_list = get_data_request(svc_url, lambda json_data: json_data['data'])

    it_list = [RSItem(id=str(it['id']), description=str(it['description']), tags=str(it["tag"]).split(" ")) for it in item_list]
    it_list_paged = it_list[curPage * pageSize: (curPage + 1) * pageSize]
    total_page = math.ceil(len(it_list) / pageSize)

    content = it_list_paged
    pagination = Pagination(curPage=curPage, pageSize=pageSize,
                            totalSize=len(it_list),
                            totalPage=total_page)

    rs_list = RecommendList(
        metadata=Metadata(type="RecommendList"),
        content=content,
        pagination=pagination
    )

    logging.info("rs_list: {}".format(rs_list))
    return rs_list


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


def init():
    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    logging.info("aws_region={}".format(aws_region))
    boto3.setup_default_session(region_name=MANDATORY_ENV_VARS['AWS_REGION'])
    global s3client
    s3client = boto3.client('s3')
    logging.info(json.dumps(s3client.list_buckets(), default=str))

    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error("Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = str(os.environ.get(var))


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    init()
    uvicorn.run(app, host="0.0.0.0", port=int(MANDATORY_ENV_VARS['RETRIEVE_PORT']))
