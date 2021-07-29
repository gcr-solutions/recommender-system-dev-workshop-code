import json
import logging
import os
import uuid
from typing import List
import sys
import cache
import math
import base64
from random import randint
from multiprocessing import Process, Pool
from threading import Thread
import boto3
import botocore

import requests
import uvicorn as uvicorn
from fastapi import FastAPI, Header, HTTPException, APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import random
import calendar
import time
from bs4 import BeautifulSoup
from functools import partial, total_ordering
from requests import ConnectTimeout
from typing import Optional
from fastapi.responses import JSONResponse

import datetime


class LoginRequest(BaseModel):
    userId: str
    userName: Optional[str] = None


class TrainRequest(BaseModel):
    change_type: str


class URLRequest(BaseModel):
    title: str


class ClickRequest(BaseModel):
    userId: str
    itemId: str


class LoadMessage(BaseModel):
    file_type: str
    file_path: str
    file_name: list = []


class LoadRequest(BaseModel):
    message: LoadMessage = None


app = FastAPI()

MANDATORY_ENV_VARS = {
    'DEMO_PORT': 5900,
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'EVENT_SERVICE_ENDPOINT': 'http://event:5100',
    'RETRIEVE_SERVICE_ENDPOINT': 'http://retrieve:5600',
    'PERSONALIZE_SERVICE_ENDPOINT': 'http://personalize:6500',
    'LOCAL_DATA_FOLDER': '/tmp/rs-data/',
    'S3_BUCKET': 'aws-gcr-rs-sol-demo-ap-southeast-1-522244679887',
    'S3_PREFIX': 'sample-data',
    'AWS_REGION': 'ap-southeast-1',
    'CLICK_RECORD_BUCKET': 'gcr-rs-ops-ap-southeast-1-522244679887',
    'CLICK_RECORD_FILE_PATH': 'system/ingest-data/action/',
    'USER_RECORD_FILE_PATH': 'system/ingest-data/user/',
    'TEST': '',
    'USE_AWS_PERSONALIZE': False
}

REDIS_KEY_USER_ID_CLICK_DICT = 'user_id_click_dict'
REDIS_KEY_USER_LOGIN_DICT = 'user_login_dict'
TRIGGER_RECALL_WINDOW = 3

news_records_dict = 'news_records_dict'
movie_records_dict = 'movie_records_dict'
user_id_action_dict = 'user_id_action_dict'

lNewsCfgCompleteType = ['news_story', 'news_culture', 'news_entertainment', 'news_sports', 'news_finance', 'news_house',
                        'news_car', 'news_edu', 'news_tech', 'news_military', 'news_travel', 'news_world',
                        'news_agriculture', 'news_game']


def xasync(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()

    return wrapper


@app.get('/api/v1/demo/dashboard', tags=["demo"])
def get_dashboard_data():
    logging.info('Start demo->get_dashboard_data()...')
    s3_bucket = MANDATORY_ENV_VARS['S3_BUCKET']
    s3_prefix = MANDATORY_ENV_VARS['S3_PREFIX']
    file_name = 'system/dashboard/dashboard.json'
    file_key = os.path.join(s3_prefix, file_name)
    s3 = boto3.resource('s3')
    object_str = s3.Object(s3_bucket, file_key).get()[
        'Body'].read().decode('utf-8')
    json_data = json.loads(object_str)
    return response_success(json_data)


# notice demo service to load news record data


@app.post('/api/v1/demo/notice', tags=["demo"])
def notice(loadRequest: LoadRequest):
    logging.info('Start demo->notice()...')

    loader_message = loadRequest.message
    file_type = loader_message.file_type
    file_path = loader_message.file_path
    file_list = loader_message.file_name
    logging.info('file type:{}, file_path:{}, file_list:{}'.format(
        file_type, file_path, file_list))
    if not os.path.exists(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']):
        logging.info("the local path {} is not existed".format(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER']))
        os.mkdir(MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'])
    if file_type == 'news_records':
        for file in file_list:
            init_news_records_data(file_type, file_path, file, news_records_dict)
    elif file_type == 'movie_records':
        for file in file_list:
            init_movie_records_data(file_type, file_path, file, movie_records_dict)

    return json.dumps({'result': 'success'}), 200, {'ContentType': 'application/json'}


@app.post('/api/v1/demo/login', tags=["demo"])
def login(loginRequest: LoginRequest):
    logging.info('Start demo->login()...')
    user_id = loginRequest.userId
    user_name = loginRequest.userName
    if user_name == None:
        s3_body = ''
        current_timestamp = str(calendar.timegm(time.gmtime()))
        temp_array = []
        temp_array.append(user_id)
        temp_array.append(get_random_sex())
        temp_array.append(get_random_age())
        temp_array.append(current_timestamp)
        temp_array.append('anonymous')
        connector = '_!_'
        s3_body = connector.join(temp_array)
        logging.info("store anonymous user data{} ".format(s3_body))

        s3client = boto3.resource('s3')
        if s3_body != '':
            s3client.Bucket(MANDATORY_ENV_VARS['CLICK_RECORD_BUCKET']).put_object(
                Key=MANDATORY_ENV_VARS['USER_RECORD_FILE_PATH'] + 'user_' + user_id + '_' + current_timestamp + '.csv',
                Body=s3_body)

        # call aws personalize addUser api
        #call_personalize_add_user(user_id, temp_array[1])

        return response_success({
            "message": "Login as anonymous user!",
            "data": {
                "userId": user_id,
                "visitCount": 1
            }
        })

    user_id_in_sever = get_user_id_by_name(user_name)
    logging.info(
        'login_post() - user_id_in_sever: {}'.format(user_id_in_sever))

    if not user_id_in_sever:
        s3_body = ''
        current_timestamp = str(calendar.timegm(time.gmtime()))
        temp_array = []
        temp_array.append(user_id)
        temp_array.append(get_random_sex())
        temp_array.append(get_random_age())
        temp_array.append(current_timestamp)
        temp_array.append(user_name)
        connector = '_!_'
        s3_body = connector.join(temp_array)
        logging.info("store anonymous user data{} ".format(s3_body))

        s3client = boto3.resource('s3')
        if s3_body != '':
            s3client.Bucket(MANDATORY_ENV_VARS['CLICK_RECORD_BUCKET']).put_object(
                Key=MANDATORY_ENV_VARS['USER_RECORD_FILE_PATH'] + 'user_' + user_id + '_' + current_timestamp + '.csv',
                Body=s3_body)

        # call aws personalize addUser api
        #call_personalize_add_user(user_id, temp_array[1])

        login_new_user(user_name, user_id)
        user_id_in_sever = user_id

    visit_count = increase_visit_count(user_name)
    response = {
        "message": "Login success",
        "data": {
            "userId": user_id_in_sever,
            "visitCount": visit_count
        }
    }
    return response_success(response)


def call_personalize_add_user(user_id, user_sex):
    logging.info("Start add new user, user id:{}, user sex:{}".format(user_id, user_sex))
    url = MANDATORY_ENV_VARS['EVENT_SERVICE_ENDPOINT'] + \
          '/api/v1/event/add_user/' + user_id

    return send_post_request(url, {
        'user_id': user_id,
        'user_sex': user_sex
    })


def get_random_sex():
    random_sex_list = ['M', 'F']
    return random_sex_list[random.randint(0, len(random_sex_list) - 1)]


def get_random_age():
    return str(random.randint(15, 60))


@app.get('/api/v1/demo/news', tags=["demo"])
def get_recommend_news(userId: str, type: str, curPage: str, pageSize: str):
    logging.info('Start demo->get_recommend_news()...')
    logging.info('user_id -> %s', userId)
    logging.info('recommend_type -> %s', type)
    user_id = userId
    recommend_type = type

    if user_id == 'magic-uuid':
        return mock_news_retrieve_response()
    logging.info('recommend news list to user')
    # get from retrieve

    logging.info("---------time before trigger retrieve:")
    logging.info(datetime.datetime.now())

    # if recommend_type == 'recommend':
    #     logging.info("---------personalize recommend---------------:")
    #     req_url=MANDATORY_ENV_VARS['PERSONALIZE_SERVICE_ENDPOINT'] + '/personalize/retrieve?user_id={}'.format(user_id)
    #     httpResp = requests.get(req_url)

    httpResp = requests.get(MANDATORY_ENV_VARS['RETRIEVE_SERVICE_ENDPOINT'] +
                            '/api/v1/retrieve/' + user_id + '?recommendType=' + recommend_type)

    logging.info("---------time after trigger retrieve:")
    logging.info(datetime.datetime.now())

    if httpResp.status_code != 200:
        return response_failed({
            "message": "Not support news type"
        }, 400)
    news_recommend_list = httpResp.json()['content']
    logging.info('new_recommend_list {}'.format(news_recommend_list))

    refresh_user_click_data(user_id, news_recommend_list, '1', recommend_type, 'news')

    retrieve_response = generate_news_retrieve_response(news_recommend_list)

    logging.info("---------time finish /news:")
    logging.info(datetime.datetime.now())

    return retrieve_response


# get user history of click


@app.get('/api/v1/demo/click/{user_id}', tags=["demo"])
def click_get(user_id: str, pageSize: str, curPage: str):
    logging.info("click_get enter")
    page_size = int(pageSize)
    cur_page = int(curPage)
    click_list_info = get_user_click_list_info(user_id, page_size, cur_page, 'news')

    return response_success({
        "message": "click history by user_id: {}".format(user_id),
        "totalItems": click_list_info['total_items'],
        "curPage": cur_page,
        "totalPage": click_list_info['total_page'],
        "data": click_list_info['click_list']
    })


@app.get('/api/v1/demo/movie/click/{user_id}', tags=["demo"])
def click_get(user_id: str, pageSize: str, curPage: str):
    logging.info("click_get enter")
    page_size = int(pageSize)
    cur_page = int(curPage)
    click_list_info = get_user_click_list_info(user_id, page_size, cur_page, 'movie')

    return response_success({
        "message": "click history by user_id: {}".format(user_id),
        "totalItems": click_list_info['total_items'],
        "curPage": cur_page,
        "totalPage": click_list_info['total_page'],
        "data": click_list_info['click_list']
    })


@app.post('/api/v1/demo/click', tags=["demo"])
def click_post(clickRequest: ClickRequest):
    logging.info("click_post enter")
    user_id = clickRequest.userId
    item_id = clickRequest.itemId
    logging.info("user_id:{}, item_id:{}".format(user_id, item_id))
    user_click_count = add_user_click_info(user_id, item_id)
    logging.info("---------time start:")
    logging.info(datetime.datetime.now())
    click_one_to_portrait(user_id, item_id)
    logging.info("---------time after portrait:")
    logging.info(datetime.datetime.now())
    click_hist_to_recall(user_id, item_id, user_click_count)

    logging.info("---------time after recall:")
    logging.info(datetime.datetime.now())
    return response_success({
        "message": "clicked item_id: {}".format(item_id)
    })


@app.get('/api/v1/demo/portrait/userid/{user_id}', tags=["demo"])
def portrait_get(user_id: str):
    logging.info("portrait_get enter")
    logging.info('user_id -> %s', user_id)
    httpResp = requests.get(
        MANDATORY_ENV_VARS['EVENT_SERVICE_ENDPOINT'] + '/api/v1/event/portrait/' + user_id)
    if httpResp.status_code != 200:
        return response_failed({
            "message": "Not support news type"
        }, 400)
    portrait_data = httpResp.json()['content']
    logging.info('portrait_data {}'.format(portrait_data))

    return {"message": "success",
            "data": portrait_data}


@app.post('/api/v1/demo/url', tags=["demo"])
def url_get(urlRequest: URLRequest):
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75',
        'Host': 'www.baidu.com',
        'upgrade-insecure-requests': '0',
        'sec-fetch-dest': 'document',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9 '
    }
    title_b64 = urlRequest.title

    decoded_bytes = base64.b64decode(title_b64)
    title_str = str(decoded_bytes, "utf-8")
    logging.info("search: {}".format(title_str))
    try:
        url = search_by_title(title_str, headers, 10)
    except Exception as e1:
        logging.error(repr(e1))
        url = ''

    random_url_list = [
        'https://baijiahao.baidu.com/s?id=1690715424093912615&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690666081179071313&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690689899754648251&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690657878159643108&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690723015618951721&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690633677458149226&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690664720265254989&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690689899754648251&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690665452297691041&wfr=spider&for=pc',
        'https://baijiahao.baidu.com/s?id=1690657878159643108&wfr=spider&for=pc',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_10036081365139924887%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9821107029074050546%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9264994315553468968%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_10001786768465709073%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9475883012444359813%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9862364227218649344%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9664070672349907696%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9039212282786529445%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9192155174958843101%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9793602629771651632%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9725620345608597043%22%7D'
        '&n_type=0&p_from=1',
        'https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_9939917266435866080%22%7D'
        '&n_type=0&p_from=1'
    ]

    logging.info(f"url: {url}")

    if not url:
        logging.warning("give a random url")
        url = random_url_list[random.randint(0, len(random_url_list) - 1)]

    return response_success({
        "url": url
    })


def search_by_title(title, headers, timeout):
    url = "http://www.baidu.com/s"
    if len(title) > 32:
        title = title[: 32]
    logging.info("search_by_title:'{}'".format(title))
    params = {"wd": title, "cl": 3, "ie": "utf-8"}

    try:
        try_count = 0
        while try_count < 10:
            res = requests.get(url, params=params, headers=headers,
                               timeout=timeout, allow_redirects=True)
            logging.info("res.status_code: {}, try_count:{}, res.text size: {}".format(res.status_code, try_count,
                                                                                       len(res.text)))
            soup = BeautifulSoup(res.text, 'html.parser')
            try_count = try_count + 1
            if is_success_code(res.status_code) and len(soup.text.strip()) > 0:
                break
            logging.info("now sleep 1 sec ...")
            time.sleep(1)
    except ConnectTimeout as e:
        logging.error(repr(e))
        logging.error("request to '{}' timeout".format(url))
        return ''

    if not is_success_code(res.status_code):
        logging.error(
            "request fail to www.baidu.com, status_code:{}".format(res.status_code))
        return ''

    content_left = soup.select("#content_left")

    if not content_left:
        logging.info("抱歉没有找到 ...")
        logging.info("res.text:{}".format(res.text.strip()))
        return ""

    logging.info("content_left div size={}".format(len(content_left)))
    url = ''

    try:
        content_left_div = content_left[0]
        all_links = content_left_div.find_all('a')
        url = find_first_link(all_links)
    except Exception as e:
        logging.error("title:{}".format(title))
        logging.error(repr(e))
    return url


def find_first_link(the_links):
    for link in the_links:
        if 'href' in link.attrs:
            href = link.attrs['href']
            if href.startswith('http://www.baidu.com/link?url='):
                return href


def is_success_code(status_code):
    return status_code in [200, 201, 202, 203, 204, 205, 206, 209, 210]


def mock_item_detail():
    item_detail_data = {
        "id": "6552368441838272771",
        "title": "Title for mock",
        "url": "www.baidu.com"
    }
    return response_success({
        "message": "mock news detail for news_id: {}".format("6552368441838272771"),
        "data": item_detail_data
    })


@xasync
def init_news_records_data(type, path, file, key):
    logging.info('start init_records_data')
    p = Pool(1)
    new_callback = partial(load_news_records_to_redis, type, key)
    p.apply_async(func=download_file_from_s3,
                  args=(MANDATORY_ENV_VARS['S3_BUCKET'], path,
                        file, MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'],),
                  callback=new_callback)

    p.close()
    p.join()


@xasync
def init_movie_records_data(type, path, file, key):
    logging.info('start init_movie_records_data')
    p = Pool(1)
    new_callback = partial(load_movie_records_to_redis, type, key)
    p.apply_async(func=download_file_from_s3,
                  args=(MANDATORY_ENV_VARS['S3_BUCKET'], path,
                        file, MANDATORY_ENV_VARS['LOCAL_DATA_FOLDER'],),
                  callback=new_callback)

    p.close()
    p.join()


def load_news_records_to_redis(type, key, file):
    try:
        file_to_load = open(file, encoding='utf8')
    except IOError as error:
        raise error

    for line in file_to_load:
        array = line.strip().split('_!_')
        if array[-1] != '':
            rCache.load_data_into_hash(key, array[0], json.dumps({
                'code': array[1],
                'type': array[2],
                'title': array[3],
                'keywords': array[4],
                'url': '-'
            }).encode('utf-8'))

    file_to_load.close()
    logging.info('Load news record... was success.')


def load_movie_records_to_redis(type, key, file):
    try:
        file_to_load = open(file, encoding='utf8')
    except IOError as error:
        raise error

    for line in file_to_load:
        array = line.strip().split('_!_')
        if array[-1] != '':
            rCache.load_data_into_hash(key, array[0], json.dumps({
                'program_type': array[1],
                'program_name': array[2],
                'release_year': array[3],
                'director': array[4],
                'actor': array[5],
                'category_property': array[6],
                'language': array[7],
                'ticket_num': array[8],
                'score': array[9],
                'level': array[10],
                'new_series': array[11]
            }).encode('utf-8'))

    file_to_load.close()
    logging.info('Load news record... was success.')


def download_file_from_s3(bucket, path, file, dest_folder):
    logging.info('Download file - %s from s3://%s/%s ... ', file, bucket, path)

    # Using default session
    s3client = boto3.client('s3')
    try:
        s3client.download_file(bucket, path + file, dest_folder + file)
    except botocore.exceptions.ClientError as error:
        raise error
    except botocore.exceptions.ParamValidationError as error:
        raise ValueError(
            'The parameters you provided are incorrect: {}'.format(error))

    logging.info(
        'Download file - %s from s3://%s/%s ... was success', file, bucket, path)
    return dest_folder + file


def click_one_to_portrait(user_id, news_id):
    url = MANDATORY_ENV_VARS['EVENT_SERVICE_ENDPOINT'] + \
          '/api/v1/event/portrait/' + user_id
    send_post_request(url, {
        'clicked_item': {
            'id': news_id
        }
    })


def click_hist_to_recall(user_id, news_id, user_click_count):
    if user_click_count > 0 and user_click_count % TRIGGER_RECALL_WINDOW == 0:
        trigger_recall_svc(user_id)


def trigger_recall_svc(user_id):
    window = TRIGGER_RECALL_WINDOW
    url = MANDATORY_ENV_VARS['EVENT_SERVICE_ENDPOINT'] + \
          '/api/v1/event/recall/' + user_id
    click_list = get_user_click_hist(user_id, window)

    return send_post_request(url, {
        'user_id': user_id,
        'clicked_item_list': click_list
    })


def get_user_click_hist(user_id, top_n):
    redis_click_list = get_list_from_redis(
        REDIS_KEY_USER_ID_CLICK_DICT, user_id)
    logging.info('get user_click_hist {}'.format(redis_click_list))
    news_id_list = [item for item in redis_click_list]
    news_id_list.reverse()
    result = []
    for var in news_id_list[0:top_n]:
        result.append({"id": var})
    return result


def send_post_request(url, data):
    logging.info("send POST request to {}".format(url))
    logging.info("data: {}".format(data))
    if MANDATORY_ENV_VARS['TEST'] == 'True':
        return "Test Mode - ok"
    headers = {'Content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    logging.info("status_code: {}".format(r.status_code))
    if r.status_code == 200:
        return r.json()
    else:
        logging.error(r.text)
        raise Exception(
            "status_code: {}, error POST request {}".format(r.status_code, url))


def add_user_click_info(user_id, news_id):
    logging.info("add_user_click_info, user_id: " +
                 user_id + ", news_id:" + news_id)
    click_list = get_list_from_redis(REDIS_KEY_USER_ID_CLICK_DICT, user_id)
    click_list.append(news_id)
    set_value_to_redis(REDIS_KEY_USER_ID_CLICK_DICT, user_id, click_list)

    logging.info("done set click_list to {} for {}, list size: {}".format(
        REDIS_KEY_USER_ID_CLICK_DICT, user_id, len(click_list)))

    update_item_click_action(user_id, news_id)

    return len(click_list)


def get_list_from_redis(dict_name, key):
    logging.info("get lsit {}[{}] from redis".format(dict_name, key))
    list_bin = rCache.get_data_from_hash(dict_name, key)
    if list_bin:
        list_values = json.loads(binary_to_str(list_bin))
    else:
        list_values = []
    logging.info("return {} items".format(len(list_values)))
    return list_values


def update_item_click_action(user_id, news_id):
    '''
    field -> user_id_action_dict
    key -> user_id
    value -> [
        {
            news_id : 0
        },
        {
            news_id : 1
        }
    ]
    '''
    logging.info("update_item_click_action {}[{}] '{}' = 1".format(
        user_id_action_dict, user_id, news_id))
    user_action = get_list_from_redis(user_id_action_dict, user_id)
    click_data = user_action['click_data']
    existed_id_flag = 0
    for item in click_data:
        if news_id in item:
            item[str(news_id)] = "1"
            existed_id_flag = 1
            break

    if existed_id_flag == 0:
        user_action['click_data'].append({news_id: '1'})
    logging.info('after user_action update: {}'.format(user_action))
    set_value_to_redis(user_id_action_dict, user_id, user_action)


def get_user_click_list_info(user_id, page_size, cur_page, scenario):
    redis_click_list = get_list_from_redis(
        REDIS_KEY_USER_ID_CLICK_DICT, user_id)
    logging.info('redis_click_list: {}'.format(redis_click_list))

    item_id_list_all = redis_click_list
    item_id_list_all.reverse()

    total_items = len(item_id_list_all)
    total_page = math.ceil(total_items / int(page_size))
    from_index = page_size * cur_page
    to_index = page_size * (cur_page + 1)
    page_item_id = item_id_list_all[from_index:to_index]
    click_list = []
    if scenario == 'news':
        click_list = [get_item_by_id(news_id) for news_id in page_item_id]
    elif scenario == 'movie':
        click_list = [get_movie_by_id(movie_id) for movie_id in page_item_id]
    else:
        logging.info("scenario {} is not supported!")

    logging.info(
        "get_user_click_list_info return click_list size: {}".format(len(click_list)))
    return {
        "click_list": click_list,
        "total_items": total_items,
        "total_page": total_page
    }


def get_item_by_id(item_id):
    logging.info("get_item_by_id start")
    news_detail_record = json.loads(rCache.get_data_from_hash(
        news_records_dict, item_id), encoding='utf-8')
    logging.info('news id {} news_detail_record {}'.format(
        item_id, news_detail_record))
    return {
        'id': item_id,
        'title': news_detail_record['title'],
        'url': 'www.baidu.com'  # TODO
    }


def get_movie_by_id(item_id):
    logging.info("get_movie_by_id start")
    movie_detail_record = json.loads(rCache.get_data_from_hash(
        movie_records_dict, item_id), encoding='utf-8')
    logging.info('movie id {} movie_detail_record {}'.format(item_id, movie_detail_record))
    s3_bucket = MANDATORY_ENV_VARS['S3_BUCKET']
    s3_prefix = MANDATORY_ENV_VARS['S3_PREFIX']
    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    return {
        'id': item_id,
        'image': 'https://{}.s3-{}.amazonaws.com/{}/movielens-posters/img/{}.jpg'.format(s3_bucket, aws_region,
                                                                                         s3_prefix, item_id),
        'title': movie_detail_record['program_name'],
        'release_year': movie_detail_record['release_year'],
        'director': movie_detail_record['director'],
        'actor': movie_detail_record['actor'],
        'category_property': movie_detail_record['category_property'],
        'new_series': movie_detail_record['new_series'],
        'level': movie_detail_record['level'],
        'desc': '{}'.format(item_id),
        'type': movie_detail_record['program_type']
    }


def get_item_detail_response(news_id):
    logging.info("get_item_detail_response start")
    news_detail_record = json.loads(rCache.get_data_from_hash(
        news_records_dict, news_id), encoding='utf-8')
    logging.info('news id {} news_detail_record {}'.format(
        news_id, news_detail_record))
    data = {
        'id': news_id,
        'title': news_detail_record['title'],
        'url': 'www.baidu.com'
    }
    return response_success({
        "message": "news {} detail success".format(news_id),
        "data": data
    })


def generate_news_retrieve_response(new_recommend_list):
    retrieve_data = []
    for element in new_recommend_list:
        news_detail_record = json.loads(rCache.get_data_from_hash(
            news_records_dict, element['id']), encoding='utf-8')
        logging.info('news id {} news_detail_record {}'.format(
            element['id'], news_detail_record))
        data = {
            'id': element['id'],
            'image': 'https://inews.gtimg.com/newsapp_bt/0/13060844390/1000',  # TODO
            'title': news_detail_record['title'],
            'desc': '{}'.format(element['id']),  # TODO
            'type': news_detail_record['type'],
            'tag': element['tags']
        }
        retrieve_data.append(data)

    return response_success({
        "message": "retrieve news list success",
        "totalItems": len(new_recommend_list),
        "curPage": 0,
        "totalPage": 1,
        "data": retrieve_data
    })


def generate_movie_retrieve_response(movie_recommend_list):
    retrieve_data = []

    s3_bucket = MANDATORY_ENV_VARS['S3_BUCKET']
    s3_prefix = MANDATORY_ENV_VARS['S3_PREFIX']
    aws_region = MANDATORY_ENV_VARS['AWS_REGION']
    for element in movie_recommend_list:
        movie_detail_record = json.loads(rCache.get_data_from_hash(
            movie_records_dict, element['id']), encoding='utf-8')
        logging.info('movie id {} movie_detail_record {}'.format(
            element['id'], movie_detail_record))

        data = {
            'id': element['id'],
            'image': 'https://{}.s3-{}.amazonaws.com/{}/movielens-posters/img/{}.jpg'.format(s3_bucket, aws_region,
                                                                                             s3_prefix, element['id']),
            'title': movie_detail_record['program_name'],
            'release_year': movie_detail_record['release_year'],
            'director': movie_detail_record['director'],
            'actor': movie_detail_record['actor'],
            'category_property': movie_detail_record['category_property'],
            'new_series': movie_detail_record['new_series'],
            'level': movie_detail_record['level'],
            'desc': '{}'.format(element['id']),
            'type': movie_detail_record['program_type'],
            'tag': element['tags']
        }
        retrieve_data.append(data)
    return response_success({
        "message": "retrieve news list success",
        "totalItems": len(movie_recommend_list),
        "curPage": 0,
        "totalPage": 1,
        "data": retrieve_data
    })


def refresh_user_click_data(user_id, items_recommend_list, action_type, action_source, scenario):
    logging.info('refresh_user_click_data start')
    store_previous_click_data(user_id, action_type, scenario)

    new_click_data = generate_new_click_data(
        items_recommend_list, action_source)

    if rCache.load_data_into_hash(user_id_action_dict, user_id, json.dumps(new_click_data).encode('utf-8')):
        logging.info(
            'Save user_id_action_dict into Redis with key : %s ', user_id)
    logging.info('refresh_user_click_data completed')


def response_failed(body, code):
    return JSONResponse(status_code=code, content=body)


def mock_news_retrieve_response():
    retrieve_data = []
    count = 0
    while (count < 20):
        retrieve_data.append(get_item_by_id("6552368441838272771"))
        count = count + 1

    return response_success({
        "message": "mock retrieve news list",
        "totalItems": 100,
        "curPage": 0,
        "totalPage": 1,
        "data": retrieve_data
    })


def mock_movie_retrieve_response():
    retrieve_data = []
    count = 0
    while (count < 20):
        retrieve_data.append(get_item_by_id("movie test id"))
        count = count + 1

    return response_success({
        "message": "mock retrieve movie list",
        "totalItems": 100,
        "curPage": 0,
        "totalPage": 1,
        "data": retrieve_data
    })


def generate_new_click_data(items_recommend_list, action_source):
    new_click_data = []
    for element in items_recommend_list:
        new_click_data.append({element['id']: '0'})
    final_click_data = {
        'click_data': new_click_data,
        'action_source': action_source
    }
    logging.info(
        'generate_new_click_data completed {}'.format(final_click_data))
    return final_click_data


def store_previous_click_data(user_id, action_type, scenario):
    logging.info('store_previous_click_data start')
    user_id_click_data_redis = rCache.get_data_from_hash(
        user_id_action_dict, user_id)
    if not bool(user_id_click_data_redis):
        return
    user_id_click_data = json.loads(user_id_click_data_redis, encoding='utf-8')
    logging.info('previous click data {}'.format(user_id_click_data))
    action_source = user_id_click_data['action_source']
    click_data = user_id_click_data['click_data']
    logging.info('previous click data action_source {}'.format(action_source))
    current_timestamp = str(calendar.timegm(time.gmtime()))
    s3_body = ''
    connector = '_!_'
    action_source_code = '0'
    for element in click_data:
        temp_array = []
        # k is item id, v is action 0/1
        for k, v in element.items():
            temp_array.append(user_id)
            temp_array.append(k)
            temp_array.append(current_timestamp)
            temp_array.append(action_type)
            temp_array.append(v)
            if action_source_code == '0':
                action_source_code = get_action_source_code(action_source, k, scenario)
            temp_array.append(action_source_code)

        s3_body = s3_body + connector.join(temp_array) + '\n'
    logging.info("store_previous_click_data data{} ".format(s3_body))

    s3client = boto3.resource('s3')
    if s3_body != '':
        s3client.Bucket(MANDATORY_ENV_VARS['CLICK_RECORD_BUCKET']).put_object(
            Key=MANDATORY_ENV_VARS['CLICK_RECORD_FILE_PATH'] + 'action_' + user_id + '_' + current_timestamp + '.csv',
            Body=s3_body)
    logging.info('store_previous_click_data completed')


def get_action_source_code(action_source, item_id, scenario):
    if action_source == 'recommend':
        return '1'
    else:
        if scenario == 'news':
            news_detail_record = json.loads(rCache.get_data_from_hash(
                news_records_dict, item_id), encoding='utf-8')
            logging.info('get item detail {}'.format(news_detail_record))
            # e.g. 106, 107..
            return news_detail_record['code']
        else:
            # e.g. 'action' or 'crime', movie type
            return action_source


def get_user_id_by_name(user_name):
    user_info_dict = get_dict_from_redis(REDIS_KEY_USER_LOGIN_DICT, user_name)
    if user_info_dict:
        return user_info_dict['user_id']
    logging.info("Cannot find user_id by name: {}".format(user_name))
    return ''


def login_new_user(user_name, user_id):
    set_value_to_redis(REDIS_KEY_USER_LOGIN_DICT, user_name, {
        "user_id": user_id,
        "visit_count": 0,
        "click_count": 0
    })


def increase_visit_count(user_name):
    user_info_dict = get_dict_from_redis(REDIS_KEY_USER_LOGIN_DICT, user_name)
    new_count = user_info_dict['visit_count'] + 1
    user_info_dict['visit_count'] = new_count
    set_value_to_redis(REDIS_KEY_USER_LOGIN_DICT, user_name, user_info_dict)
    logging.info("user_name:{}, visit_count: {}".format(user_name, new_count))
    return new_count


def set_value_to_redis(dict_name, key, value):
    rCache.load_data_into_hash(dict_name, key, json.dumps(value))


def get_dict_from_redis(dict_name, key):
    logging.info("get dict {}[{}] from redis".format(dict_name, key))
    val_bin = rCache.get_data_from_hash(dict_name, key)
    if val_bin:
        val_dict = json.loads(binary_to_str(val_bin))
    else:
        val_dict = {}
    logging.info("return {}".format(len(val_dict)))
    return val_dict


def response_success(body):
    return body


def binary_to_str(bin_str):
    return bin_str.decode('utf-8')


# movie
@app.get('/api/v1/demo/movie', tags=["demo"])
def get_recommend_movie(userId: str, type: str, curPage: str, pageSize: str):
    logging.info('Start demo->get_recommend_movie()...')
    logging.info('user_id -> %s', userId)
    logging.info('recommend_type -> %s', type)
    user_id = userId
    recommend_type = type

    if user_id == 'magic-uuid':
        return mock_news_retrieve_response()
    logging.info('recommend movie list to user')
    # get from retrieve
    httpResp = requests.get(MANDATORY_ENV_VARS['RETRIEVE_SERVICE_ENDPOINT'] +
                            '/api/v1/retrieve/' + user_id + '?recommendType=' + recommend_type)
    if httpResp.status_code != 200:
        return response_failed({
            "message": "Not support news type"
        }, 400)
    movie_recommend_list = httpResp.json()['content']
    logging.info('movie_recommend_list {}'.format(movie_recommend_list))

    refresh_user_click_data(user_id, movie_recommend_list, '1', recommend_type, 'movie')

    retrieve_response = generate_movie_retrieve_response(movie_recommend_list)

    return retrieve_response


@app.post('/api/v1/demo/start_train', tags=["demo"])
def start_train_post(trainReq: TrainRequest):
    logging.info('demo start_train_post start! change type: {}'.format(
        trainReq.change_type))
    if trainReq.change_type not in ['MODEL', 'CONTENT', 'ACTION']:
        raise HTTPException(status_code=405, detail="invalid change_type")

    url = MANDATORY_ENV_VARS['EVENT_SERVICE_ENDPOINT'] + \
          '/api/v1/event/start_train'
    result = send_post_request(url, {
        'change_type': trainReq.change_type
    })
    logging.info('executionArn: {}'.format(result['executionArn']))
    response = {
        "message": "Start train success",
        "data": result
    }
    return response


@app.get('/api/v1/demo/offline_status/{executionArn}', tags=["demo"])
def offline_status(executionArn: str):
    logging.info("offline_status start, executionArn {}".format(executionArn))
    httpResp = requests.get(
        MANDATORY_ENV_VARS['EVENT_SERVICE_ENDPOINT'] + '/api/v1/event/offline_status/' + executionArn)
    if httpResp.status_code != 200:
        return response_failed({
            "message": "Error"
        }, 400)
    result = httpResp.json()['status']
    logging.info('result {}'.format(result))
    return result


def init():
    # Check out environments
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            logging.error(
                "Mandatory variable {%s} is not set, using default value {%s}.", var, MANDATORY_ENV_VARS[var])
        else:
            MANDATORY_ENV_VARS[var] = os.environ.get(var)

    # Initial redis connection
    global rCache
    rCache = cache.RedisCache(
        host=MANDATORY_ENV_VARS['REDIS_HOST'], port=MANDATORY_ENV_VARS['REDIS_PORT'])

    logging.info('redis status is {}'.format(rCache.connection_status()))

    logging.info('demo service start')


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    init()
    uvicorn.run(app, host="0.0.0.0", port=MANDATORY_ENV_VARS['DEMO_PORT'])
