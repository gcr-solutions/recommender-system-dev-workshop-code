import logging
import numpy as np
import json
import itertools

logging.basicConfig(level=logging.INFO)


class ServiceImpl:

    def __init__(self,
                 recall_per_news_id=10,
                 similar_entity_threshold=20,
                 recall_threshold=2.0,
                 recall_merge_number=20,
                 entity_index_l={},
                 word_index_l={},
                 entity_embedding_l=[]):

        logging.info('Initial Service implementation...')
        logging.info(
            'recall_per_news_id = %s, similar_entity_threshold=%s, recall_threshold=%s, recall_merge_number=%s',
            recall_per_news_id,
            similar_entity_threshold,
            recall_threshold,
            recall_merge_number
            )
        #
        self.recall_per_news_id = int(recall_per_news_id)
        self.similar_entity_threshold = int(similar_entity_threshold)
        self.recall_threshold = float(recall_threshold)
        self.recall_merge_number = int(recall_merge_number)
        self.entity_index = entity_index_l
        self.word_index = word_index_l
        self.entity_embedding = entity_embedding_l

    def analyze_shot_record(self, record, id):
        if id in record.keys():
            current_count = record[id]
            record[id] = record[id] + 1
        else:
            record[id] = 1

    # 根据召回位置打分；记录命中的次数；去重
    def recall_pos_score(self, src_item, topn_list, param, shot_record):
        list_with_score = []
        for pos, idx in enumerate(topn_list):
            if src_item != str(idx):
                current_idx_with_score = {}
                current_idx_with_score['id'] = str(idx)
                current_idx_with_score['score'] = (len(topn_list) - 1 - pos) * param['w'] + param['b']
                self.analyze_shot_record(shot_record, str(idx))
                list_with_score.append(current_idx_with_score)
        return list_with_score

    def recall_by_popularity(self, news_ids, recall_wrap, recall_items, multiple_shot_record):
        # 根据最近阅读的记录召回
        # 1. category: 类别
        # 2. director: 导演
        # 3. actor: 演员
        # 4. language: 语言
        # 5. level: 分级 
        # 6. year: 年限 
        dict_id_content = recall_wrap['content']
        dict_wrap = recall_wrap['dict_wrap']
        topn_wrap = recall_wrap['config']['mt_topn']
        weights = recall_wrap['config']['pos_weights']
        popularity_method_list = recall_wrap['config']['pop_mt_list']
        for news_id in news_ids:
            for mt in popularity_method_list:
                src_item = news_id
                current_prop = dict_id_content[src_item][mt]
                logging.info(
                    "top n {} method with following {}".format(mt, current_prop))
                single_recall_result = {}
                current_list_with_score = []
                if current_prop[0] != None:
                    for prop in current_prop:
                        current_list_with_score = current_list_with_score + \
                                                  self.recall_pos_score(src_item,
                                                                        dict_wrap[mt][prop][0:topn_wrap[mt]],
                                                                        weights[mt], multiple_shot_record)
                    single_recall_result['method'] = mt
                    single_recall_result['list'] = current_list_with_score
                    logging.info("method {} find {} candidates".format(
                        mt, len(current_list_with_score)))
                    recall_items.append(single_recall_result)

    def recall_by_portrait(self, user_portrait, recall_wrap, recall_items, multiple_shot_record):
        # 根据用户画像做热门召回
        # 1. category: 类别
        # 2. director: 导演
        # 3. actor: 演员
        # 4. language: 语言
        # 5. level: 分级 
        # 6. year: 年限 
        # 7. review: 评论/描述
        # 8. photo: 海报 
        # 9. ub: 用户行为/双塔模型
        dict_wrap = recall_wrap['dict_wrap']
        topn_wrap = recall_wrap['config']['mt_topn']
        weights = recall_wrap['config']['pos_weights']
        portrait_method_list = recall_wrap['config']['portrait_mt_list']
        for mt in portrait_method_list:
            current_prop = user_portrait[mt]
            logging.info(
                "top n user portrait {} method with following {}".format(mt, current_prop))
            single_recall_result = {}
            current_list_with_score = []
            if current_prop['recent'] != None:
                user_mt = "portrait_{}".format(mt)
                for prop in current_prop['recent'][0]:
                    if prop and dict_wrap[mt].get(prop):
                        current_list_with_score = current_list_with_score + \
                                                  self.recall_pos_score(None,
                                                                        dict_wrap[mt][prop][0:topn_wrap[user_mt]],
                                                                        weights[user_mt], multiple_shot_record)
                    else:
                        logging.warning("cannot find '{}' in dict_wrap[{}]".format(prop, mt))

                single_recall_result['method'] = user_mt
                single_recall_result['list'] = current_list_with_score
                logging.info("portrait method {} find {} candidates".format(
                    mt, len(current_list_with_score)))
                recall_items.append(single_recall_result)
        # 根据用户画像做相似性召回
        # 1. ub: 用户行为/YoutubeDNN
        user_ub_embedding = user_portrait['ub_embeddding']
        ub_faiss_index = recall_wrap['ub_index']
        ub_idx_mapping = recall_wrap['ub_idx_mapping']
        D, I = ub_faiss_index.search(np.ascontiguousarray(user_ub_embedding), topn_wrap['portrait_ub'])
        # mapping index code to item code
        single_recall_result = {}
        single_recall_result['method'] = 'portrait_ub'
        single_recall_result['list'] = []
        for d, i in zip(D[0], I[0]):
            map_idx = ub_idx_mapping[i]
            current_idx_with_score = {}
            current_idx_with_score['id'] = map_idx
            current_idx_with_score['score'] = d
            self.analyze_shot_record(multiple_shot_record, map_idx)
            single_recall_result['list'].append(current_idx_with_score)
        recall_items.append(single_recall_result)

    def merge_recall_result(self, news_ids, **config_dict):
        ########################################
        # 召回融合排序逻辑
        ########################################
        recall_wrap = config_dict['recall_wrap']
        user_portrait = config_dict['user_portrait']

        recall_items = []
        multiple_shot_record = {}
        # 根据最近阅读的历史做召回
        self.recall_by_popularity(news_ids, recall_wrap, recall_items, multiple_shot_record)
        # 根据用户画像做召回
        self.recall_by_portrait(user_portrait, recall_wrap, recall_items, multiple_shot_record)

        # recall_merge_cnt = 100
        n_last_len = recall_wrap['config']['merge_cnt']
        method_weights = recall_wrap['config']['mt_weights']
        raw_item_list = {}

        for mt_list in recall_items:
            mt = mt_list['method']
            list_result = mt_list['list']
            method_weight = method_weights[mt]
            for idx, id_with_score in enumerate(list_result):
                current_id = id_with_score['id']
                current_score = id_with_score['score']
                multiple_shot_score = multiple_shot_record[current_id]
                whole_score = method_weight * \
                              (current_score + multiple_shot_score)
                current_result = []
                current_result.append(current_id)
                current_result.append(mt)
                current_result.append(idx)
                current_result.append(whole_score)
                # update raw list
                if current_id in raw_item_list.keys():
                    if whole_score > raw_item_list[current_id][3]:
                        raw_item_list[current_id] = current_result
                else:
                    raw_item_list[current_id] = current_result

        # 根据最终得分进行排序
        sort_item_list = dict(
            sorted(raw_item_list.items(), key=lambda item: item[1][3], reverse=True))

        logging.info("sort {} result is {}".format(
            len(sort_item_list), sort_item_list))

        recall_result = {}

        # 截取前recall_merge_cnt的结果作为recall的结果
        recall_result = dict(itertools.islice(sort_item_list.items(), n_last_len))

        logging.info('Recall has done & return -> {}'.format(recall_result))
        return recall_result
