
import logging
from random import sample
import numpy as np
import json


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
        logging.info('recall_per_news_id = %s, similar_entity_threshold=%s, recall_threshold=%s, recall_merge_number=%s',
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

    def rm_duplicate(self, raw_list, raw_id):
        raw_list = list(dict.fromkeys(raw_list))
        if raw_id in raw_list:
            raw_list.remove(raw_id)
        return raw_list

    def rm_duplicate_sample(self, current, whole):
        current_cp = {**current}
        for key, value in current_cp.items():
            for wk, wv in whole.items():
                if key in wv.keys():
                    del current[key]
                    # current.pop(key, None)

    def random_pick_list(self, raw_list, num):
        if len(raw_list) <= num:
            return raw_list, num-len(raw_list)
        else:
            return sample(raw_list, num), 0

    def pickup_random_list(self, keywords, num, dict_keywords_id):
        k_list = keywords.split(',')
        raw_list = []
        for k in k_list:
            logging.info('pickup_random_list :: key -> %s', k)
            pick_list, _ = self.random_pick_list(dict_keywords_id[str(k)], num)
            raw_list = raw_list + pick_list
        return raw_list

    def sample_same_entity(self, current_sample, item, **kwargs):
        dict_id_entity = kwargs['id_entity']
        dict_entity_id = kwargs['entity_id']
        sample_num = kwargs['sample_num']
        whole_sample = kwargs['whole_sample']
        for entity in list(dict.fromkeys(dict_id_entity[str(item)])):
            if entity != 0:
                # sample from same entity
                self.sample_random_to_dict(
                    current_sample, dict_entity_id[entity], sample_num, 0)
        # remvoe duplicate
        logging.info("!!!!!!!!!!!same entity current sample recall for {} and  whole sample {}".format(
            current_sample, whole_sample))
        self.rm_duplicate_sample(current_sample, whole_sample)
        logging.info("debug finish rm logic")

    def sample_similar_entity(self, current_sample, item, index, embed, **kwargs):
        dict_id_entity = kwargs['id_entity']
        dict_entity_id = kwargs['entity_id']
        sample_num = kwargs['sample_num']
        whole_sample = kwargs['whole_sample']
        similar_entity_threshold = kwargs['similar_entity_threshold']
        # sample from similar entity
        for entity in list(dict.fromkeys(dict_id_entity[str(item)])):
            if entity != 0:
                logging.info('entity -> {}, item -> {}'.format(entity, item))
                logging.info('type(embed[entity]) -> {}'.format(type(embed[entity])))
                logging.info('type([embed[entity]]) -> {}'.format(type([embed[entity]])))
                dist, indices = self.find_near_vector(
                    index, np.array([embed[entity]]), similar_entity_threshold)
                for n in range(len(indices)):
                    if n != 0 and indices[n] in dict_entity_id:
                        self.sample_random_to_dict(
                            current_sample, dict_entity_id[indices[n]], sample_num, 1)
        # remove duplicate
        self.rm_duplicate_sample(current_sample, whole_sample)

    def sample_same_word(self, current_sample, item, **kwargs):
        dict_id_word = kwargs['id_word']
        dict_word_id = kwargs['word_id']
        sample_num = kwargs['sample_num']
        whole_sample = kwargs['whole_sample']
        for word in list(dict.fromkeys(dict_id_word[str(item)])):
            if word != 0:
                # sample from same word
                self.sample_random_to_dict(
                    current_sample, dict_word_id[word], sample_num, 2)
        # remvoe duplicate
        self.rm_duplicate_sample(current_sample, whole_sample)

    def sample_random_to_dict(self, current, sample_list, num_to_sample, sample_type):
        current_list, _ = self.random_pick_list(sample_list, num_to_sample)
        for cl in current_list:
            if cl not in current:
                current[cl] = sample_type

    def find_near_vector(self, index, query_vectors, k):
        logging.info('type(index) -> {}, query_vectors -> {}'.format(type(index),query_vectors))
        distances, indices = index.search(query_vectors, k)
        return distances, indices

    def random_pick_dict(self, current_sample, recall_per_item):
        keys = sample(list(current_sample), recall_per_item)
        new_sample = {}
        for k in keys:
            new_sample[k] = current_sample[k]
        return new_sample

    # 1st recall, sample from type
    def first_recall(self, news_ids, news_id_news_type_dict, news_type_news_ids_dict):
        logging.info('Start first_recall with news_ids -> %s', news_ids)
        type_sample_list = []
        for news_id in news_ids:
            type_sample_list = type_sample_list + \
                self.pickup_random_list(
                    news_id_news_type_dict[str(news_id)], 1, news_type_news_ids_dict)
            type_sample_list = self.rm_duplicate(type_sample_list, str(news_id))

        first_recall_result = []
        for news_id in type_sample_list:
            first_recall_result.append([news_id, 'type'])
        logging.info('first_recall has done')
        return first_recall_result

    # 2nd recall, sample from keywords
    def second_recall(self, news_ids, news_id_keywords_dict, keyword_news_ids_dict):
        logging.info('Start second_recall with news_ids -> %s', news_ids)
        keywords_sample_list = []
        for news_id in news_ids:
            keywords_sample_list = keywords_sample_list + \
                self.pickup_random_list(
                    news_id_keywords_dict[str(news_id)], 1, keyword_news_ids_dict)
            keywords_sample_list = self.rm_duplicate(
                keywords_sample_list, str(news_id))

        second_recall_result = []
        for news_id in keywords_sample_list:
            second_recall_result.append([news_id, 'keyword'])
        logging.info('second_recall has done')
        return second_recall_result

    # 3rd recall, sample from semantic
    def third_recall(self, news_ids, news_id_word_ids_dict, news_id_entity_ids_dict, word_id_news_ids_dict, entity_id_news_ids_dict):
        logging.info('Start third_recall with news_ids -> %s', news_ids)
        # entity_list = []
        sample_from_semantic = {}
        dict_params = {}
        dict_params['id_word'] = news_id_word_ids_dict
        dict_params['id_entity'] = news_id_entity_ids_dict
        dict_params['word_id'] = word_id_news_ids_dict
        dict_params['entity_id'] = entity_id_news_ids_dict
        dict_params['sample_num'] = self.recall_per_news_id
        dict_params['whole_sample'] = sample_from_semantic
        dict_params['similar_entity_threshold'] = self.similar_entity_threshold
        for news_id in news_ids:
            current_sample = {}
            # 1st part based on same entity: type 0
            self.sample_same_entity(current_sample, news_id, **dict_params)
            if len(current_sample) < self.recall_per_news_id:
                # 2nd part based on similary enity within simialry_entity_threshold: type 1
                logging.info('!!!!!!!!!!!debug current sample {} news_id {} entity_index {}'.format(current_sample, news_id, self.entity_index))
                self.sample_similar_entity(current_sample, news_id,
                                           self.entity_index, self.entity_embedding, **dict_params)
            if len(current_sample) < self.recall_per_news_id:
                # 3rd part based on same word: type 2
                self.sample_same_word(current_sample, news_id, **dict_params)
            if len(current_sample) > self.recall_per_news_id:
                sample_from_semantic[news_id] = self.random_pick_dict(
                    current_sample, self.recall_per_news_id)
            else:
                sample_from_semantic[news_id] = current_sample
        logging.info(sample_from_semantic)

        third_recall_result = []
        for _, src_item_value in sample_from_semantic.items():
            for recall_key, recall_value in src_item_value.items():
                third_recall_result.append(
                    [recall_key, 'entity_{}'.format(recall_value)])
        logging.info('third_recall has done')
        return third_recall_result

    # 4th recall, sample based on user portrait
    def fourth_recall(self, user_portrait_data, keyword_news_ids_dict):
        logging.info(
            'Start fourth_recall with user_id_portrait -> %s', user_portrait_data)
        portrait_sample_list = []
        filter_keyword_list = []
        # if not bool(user_id_portrait):
        if user_portrait_data != None and not bool(user_portrait_data):
            # user_id_portrait = json.loads(user_portrait_data.decode('utf-8'))
            user_id_portrait = user_portrait_data
            for k, v in user_id_portrait.items():
                for kw, sc in v.items():
                    if sc > self.recall_threshold and kw != 'avg':
                        filter_keyword_list.append(kw)
            portrait_sample_list = self.pickup_random_list(
                ','.join(filter_keyword_list), 1, keyword_news_ids_dict)

        fourth_recall_result = []
        for news_id in portrait_sample_list:
            fourth_recall_result.append([news_id, 'user_portrait'])
        logging.info('fourth_recall has done')
        return fourth_recall_result

    # Merge recall result and return limited
    def merge_recall_result(self, news_ids,
                            news_id_word_ids_dict,
                            news_id_entity_ids_dict,
                            word_id_news_ids_dict,
                            entity_id_news_ids_dict,
                            news_id_keywords_dict,
                            news_id_news_type_dict,
                            news_type_news_ids_dict,
                            user_portrait,
                            keyword_news_ids_dict):
        # Priority: entity_0 -> keyword -> type -> user_portrait -> entity_1|2
        logging.info(
            'Start recall : priority[ entity_0 -> keyword -> type -> user_portrait -> entity_1|2 ] ...')
        recall_result = []
        third = self.third_recall(news_ids, news_id_word_ids_dict,
                                  news_id_entity_ids_dict, word_id_news_ids_dict, entity_id_news_ids_dict)
        for ret in third:
            if ret[1] == 'entity_0':
                recall_result.append(ret)
        for ret in self.second_recall(news_ids, news_id_keywords_dict, keyword_news_ids_dict):
            recall_result.append(ret)
        for ret in self.first_recall(news_ids, news_id_news_type_dict, news_type_news_ids_dict):
            recall_result.append(ret)
        for ret in self.fourth_recall(user_portrait, keyword_news_ids_dict):
            recall_result.append(ret)
        for ret in third:
            if ret[1] != 'entity_0':
                recall_result.append(ret)
        logging.info('Recall has done & return -> {}'.format(recall_result))
        return recall_result[0:self.recall_merge_number]
