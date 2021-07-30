# importing libraries
import argparse
import logging
import os
import pickle
from random import sample

import boto3

########################################
# 从s3同步数据
########################################

def sync_s3(file_name_list, s3_folder, local_folder):
    for f in file_name_list:
        print("file preparation: download src key {} to dst key {}".format(os.path.join(
            s3_folder, f), os.path.join(local_folder, f)))
        s3client.download_file(bucket, os.path.join(
            s3_folder, f), os.path.join(local_folder, f))


def write_to_s3(filename, bucket, key):
    print("upload s3://{}/{}".format(bucket, key))
    with open(filename, 'rb') as f:  # Read in binary mode
        # return s3client.upload_fileobj(f, bucket, key)
        return s3client.put_object(
            ACL='bucket-owner-full-control',
            Bucket=bucket,
            Key=key,
            Body=f
        )


def write_str_to_s3(content, bucket, key):
    print("write s3://{}/{}, content={}".format(bucket, key, content))
    s3client.put_object(Body=str(content).encode("utf8"), Bucket=bucket, Key=key, ACL='bucket-owner-full-control')


parser = argparse.ArgumentParser(description="app inputs and outputs")
parser.add_argument("--bucket", type=str, help="s3 bucket")
parser.add_argument("--prefix", type=str, help="s3 input key prefix")
parser.add_argument("--region", type=str, help="aws region")
args, _ = parser.parse_known_args()
print("args:", args)

if args.region:
    print("region:", args.region)
    boto3.setup_default_session(region_name=args.region)

bucket = args.bucket
prefix = args.prefix
if prefix.endswith("/"):
    prefix = prefix[:-1]

print(f"bucket:{bucket}, prefix:{prefix}")

s3client = boto3.client('s3')

local_folder = 'info'
if not os.path.exists(local_folder):
    os.makedirs(local_folder)
# recall & rank 结果加载
file_name_list = ['recall_batch_result.pickle', 'rank_batch_result.pickle']
s3_folder = '{}/feature/recommend-list/movie'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# 倒排列表的pickle文件
file_name_list = ['movie_id_movie_property_dict.pickle',
                  'movie_category_movie_ids_dict.pickle']
s3_folder = '{}/feature/content/inverted-list/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)
# filter配置项
file_name_list = ['filter_config.pickle']
s3_folder = '{}/model/filter/'.format(prefix)
sync_s3(file_name_list, s3_folder, local_folder)

# 加载pickle文件
file_to_load = open("info/movie_id_movie_property_dict.pickle", "rb")
dict_id_content = pickle.load(file_to_load)
print("length of movie_id v.s. movie_property {}".format(len(dict_id_content)))

file_to_load = open("info/movie_category_movie_ids_dict.pickle", "rb")
dict_category_id = pickle.load(file_to_load)
print("length of movie_category v.s. movie_ids {}".format(len(dict_category_id)))

# 加载filter配置
file_to_load = open("info/filter_config.pickle", "rb")
filter_config = pickle.load(file_to_load)
print("length of filter_config {}".format(len(filter_config)))

# 加载recall结果
file_to_load = open("info/recall_batch_result.pickle", "rb")
dict_recall_result = pickle.load(file_to_load)

# 加载rank结果
file_to_load = open("info/rank_batch_result.pickle", "rb")
dict_rank_result = pickle.load(file_to_load)


# 返回结果格式设计：
# item_id | recall_type | recall_score | rank_type | rank_score | filter_type | filter_score

# recall_type: [运行时机]_[方法]_[位置]
# [运行时机]: batch/online
# [方法]: category/director/actor/language/level/year/review/photo/ub/portrai_xxx
# [位置]: 数字[0-xxx]

# recall_score: 召回得分，float型

# rank_type: [运行时机]_[方法]_[位置]
# [运行时机]: batch/online
# [数据源头]: action/portrait
# [方法]: deepfm/xgboost
# [位置]: 数字[0-xxx]

# rank_score: 排序得分，float型

# filter_type: [运行时机]_[方法]_[位置]
# [运行时机]: batch/online
# [方法]: recommend/coldstart/disparity
# [位置]: 数字[0-xxx]

# filter_score: 过滤得分，float型

def get_dict_pos(key, dict_var):
    return list(dict_var.keys()).index(key)


def calc_filter_score(recall_score, rank_score, recall_mt=None, rank_mt=None, recall_pos=None, rank_pos=None):
    filter_score = min(1.0, recall_score / 40.0 + rank_score)
    return round(filter_score, 2)


def mt_construct(timing, mt, pos):
    type_list = []
    type_list.append(str(timing))
    type_list.append(str(mt))
    type_list.append(str(pos))
    type_name = '_'.join(type_list)
    return type_name


def sort_and_fill_pos(filter_result):
    sort_filter_result = dict(
        sorted(filter_result.items(), key=lambda item: item[1][2], reverse=True))
    filter_pos = 0
    update_filter_result = dict()
    for filter_id, filter_content in sort_filter_result.items():
        current_trace = filter_content[3]
        current_trace_split_list = current_trace.split('|')
        current_filter_type = current_trace_split_list[4]
        current_filter_type_split_list = current_filter_type.split('_')
        update_filter_type_split_list = current_filter_type_split_list
        update_filter_type_split_list[2] = str(filter_pos)
        update_filter_type = '_'.join(update_filter_type_split_list)
        update_trace_split_list = current_trace_split_list
        update_trace_split_list[-2] = update_filter_type
        update_trace = '|'.join(update_trace_split_list)
        update_filter_content = filter_content
        update_filter_content[3] = update_trace
        #         print("update id {} trace {} type {}".format(filter_id, update_trace,update_filter_type_split_list))
        update_filter_result[str(filter_id)] = update_filter_content
        # update filter pos
        filter_pos = filter_pos + 1


def initial_diversity(stats_result, filter_config):
    for cate in filter_config['category']:
        stats_result[cate] = 0


def category_diversity_logic(filter_result, stats_result, dict_category_id, filter_config):
    diversity_count = filter_config['category_diversity_count']
    min_category = None
    min_category_count = 999
    candidate_category_list = []
    for cate, count in stats_result.items():
        if count < min_category_count and count != 0:
            min_category_count = count
            min_category = cate
        elif count == 0:
            candidate_category_list.append(cate)
    if min_category != None:
        candidate_category_list.append(min_category)
    diversity_result_list = []
    diversity_result_content_list = []
    current_diversity_count = 0

    filter_result_list = list(filter_result.keys())
    filter_result_content_list = list(filter_result.values())
    sample_try = 0
    catch_count = 0
    while catch_count < diversity_count:
        for cate in candidate_category_list:
            if str(cate) not in dict_category_id:
                print("Warning: cannot find {} dict_category_id".format(cate))
                continue
            sample_try = sample_try + 1
            candidate_id = sample(dict_category_id[str(cate)], 1)[0]
            if candidate_id in filter_result_list:
                continue
            else:
                filter_result_list.append(str(candidate_id))
                filter_result_content_list.append([str(candidate_id), 'diversity', 0.0,
                                                   'batch_diversity_{}|{}'.format(len(filter_result_list), cate)])
                catch_count = catch_count + 1
                if catch_count >= diversity_count:
                    break
        if sample_try > 5 * diversity_count:
            logging.error(
                "fail to find enough diversity candidate, need to find {} but only find {}".format(diversity_count,
                                                                                                   catch_count + 1))
            break

    update_filter_result = dict(zip(filter_result_list, filter_result_content_list))
    return update_filter_result


# 同一批次去重/统计
# 运行时机
run_timing = 'batch'
dict_filter_result = {}
for user_id, recall_result in dict_recall_result.items():
    # print("user id {}".format(user_id))
    current_user_result = {}
    current_diversity_result = {}
    initial_diversity(current_diversity_result, filter_config)
    for recall_id, recall_property in recall_result.items():
        # print("item id {}".format(recall_id))
        # print("dict rank result {}".format(dict_rank_result[str(user_id)]))
        # 构建recall_type
        recall_type = mt_construct(run_timing, recall_property[1], recall_property[2])
        # 构建recall_score
        recall_score = round(recall_property[3], 2)
        # 构建rank_type
        rank_pos = str(get_dict_pos(int(recall_id), dict_rank_result[str(user_id)]))
        rank_type = mt_construct(run_timing, 'deepfm', rank_pos)
        # 构建rank_score
        rank_score = round(dict_rank_result[str(user_id)][int(recall_id)], 2)
        # 构建filter_type
        filter_type = mt_construct(run_timing, 'recommend', 'TBD')
        # 构建filter_score
        filter_score = calc_filter_score(recall_score, rank_score)
        #         print("{}|{}|{}|{}|{}|{}".format(recall_type,recall_score,rank_type,rank_score))
        #         break
        recommend_trace = "{}|{}|{}|{}|{}|{}".format(recall_type, recall_score, rank_type, rank_score, filter_type,
                                                     filter_score)
        current_user_result[str(recall_id)] = []
        current_user_result[str(recall_id)].append(str(recall_id))
        current_user_result[str(recall_id)].append('recommend')
        current_user_result[str(recall_id)].append(filter_score)
        current_user_result[str(recall_id)].append(recommend_trace)
        # 更新多样性统计
        current_category = dict_id_content[str(recall_id)]['category']
        for cate in current_category:
            if cate is not None and len(str(cate)) > 0:
                current_diversity_result[cate] = current_diversity_result.get(cate, 0) + 1
    # 根据filter score更新排序
    sort_and_fill_pos(current_user_result)
    update_user_result = category_diversity_logic(current_user_result, current_diversity_result, dict_category_id,
                                                  filter_config)
    dict_filter_result[str(user_id)] = update_user_result

file_name = 'info/filter_batch_result.pickle'
output_file = open(file_name, 'wb')
pickle.dump(dict_filter_result, output_file)
output_file.close()

write_to_s3(file_name,
            bucket,
            '{}/feature/recommend-list/movie/filter_batch_result.pickle'.format(prefix))
