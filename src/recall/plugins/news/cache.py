
import redis
import logging
import pickle



class RedisCache:

    # Pickle content
    news_id_keywords_tfidf = 'news_id_keywords_tfidf_dict'
    entity_id_news_ids = 'entity_id_news_ids_dict'
    news_id_entity_ids = 'news_id_entity_ids_dict'
    news_id_keywords = 'news_id_keywords_dict'
    news_id_news_title = 'news_id_news_title_dict'
    news_id_news_type = 'news_id_news_type_dict'
    news_id_word_ids = 'news_id_word_ids_dict'
    keyword_news_ids = 'keyword_news_ids_dict'
    news_type_news_ids = 'news_type_news_ids_dict'
    word_id_news_ids = 'word_id_news_ids_dict'

    # Others' content
    user_id_protrait = 'user_id_portrait_dict'


    def __init__(self, host='localhost', port=6379, db=0):
        logging.info('Initial RedisCache ...')
        # Initial connection to Redis
        logging.info('Connect to Redis %s:%s ...', host, port)
        self.rCon = redis.Redis(host=host, port=port, db=db)

        # Dictionary
        self.news_id_keywords_tfidf_dict_local = {}
        self.entity_id_news_ids_dict_local = {}
        self.news_id_entity_ids_dict_local = {}
        self.news_id_keywords_dict_local = {}
        self.news_id_news_title_dict_local = {}
        self.news_id_news_type_dict_local = {}
        self.news_id_word_ids_dict_local = {}
        self.keyword_news_ids_dict_local = {}
        self.news_type_news_ids_dict_local = {}
        self.word_id_news_ids_dict_local = {}


    def connection_status(self):
        return self.rCon.client_list()

    def get_keywords(self, news_ids):
        keywords = []
        for news_id in news_ids:
            keywords.append(self.news_id_keywords_dict()[news_id])
            # keywords = keywords + self.news_id_keywords_dict()[news_id]
        return keywords

    def get_content_type(self, news_id):
        return self.news_id_news_type_dict()[news_id]
    
    def get_news_id_keywords_tfidf_dict(self, news_id):
        return self.news_id_keywords_tfidf_dict()[news_id]

    def get_user_portrait(self, user_id):
        return self.rCon.hget(self.user_id_protrait, user_id)
    
    def save_user_portrait(self, user_id, user_portrait):
        return self.rCon.hset(self.user_id_protrait, user_id, user_portrait)

    def news_id_keywords_tfidf_dict(self):
        if not bool(self.news_id_keywords_tfidf_dict_local):
            self.news_id_keywords_tfidf_dict_local = pickle.loads(self.rCon.get(self.news_id_keywords_tfidf))
            if not len(self.news_id_keywords_tfidf_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_id_keywords_tfidf)
        return self.news_id_keywords_tfidf_dict_local
        
    def entity_id_news_ids_dict(self):
        if not bool(self.entity_id_news_ids_dict_local):
            self.entity_id_news_ids_dict_local = pickle.loads(self.rCon.get(self.entity_id_news_ids))
            if not len(self.entity_id_news_ids_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.entity_id_news_ids)
        return self.entity_id_news_ids_dict_local

    def news_id_entity_ids_dict(self):
        if not bool(self.news_id_entity_ids_dict_local):
            self.news_id_entity_ids_dict_local = pickle.loads(self.rCon.get(self.news_id_entity_ids))
            if not len(self.news_id_entity_ids_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_id_entity_ids)
        return self.news_id_entity_ids_dict_local

    def news_id_keywords_dict(self):
        if not bool(self.news_id_keywords_dict_local):
            self.news_id_keywords_dict_local = pickle.loads(self.rCon.get(self.news_id_keywords))
            if not len(self.news_id_keywords_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_id_keywords)
        return self.news_id_keywords_dict_local

    def news_id_news_title_dict(self):
        if not bool(self.news_id_news_title_dict_local):
            self.news_id_news_title_dict_local = pickle.loads(self.rCon.get(self.news_id_news_title))
            if not len(self.news_id_news_title_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_id_news_title)
        return self.news_id_news_title_dict_local

    def news_id_news_type_dict(self):
        if not bool(self.news_id_news_type_dict_local):
            self.news_id_news_type_dict_local = pickle.loads(self.rCon.get(self.news_id_news_type))
            if not len(self.news_id_news_type_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_id_news_type)
        return self.news_id_news_type_dict_local

    def news_id_word_ids_dict(self):
        if not bool(self.news_id_word_ids_dict_local):
            self.news_id_word_ids_dict_local = pickle.loads(self.rCon.get(self.news_id_word_ids))
            if not len(self.news_id_word_ids_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_id_word_ids)
        return self.news_id_word_ids_dict_local

    def keyword_news_ids_dict(self):
        if not bool(self.keyword_news_ids_dict_local):
            self.keyword_news_ids_dict_local = pickle.loads(self.rCon.get(self.keyword_news_ids))
            if not len(self.keyword_news_ids_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.keyword_news_ids)
        return self.keyword_news_ids_dict_local

    def news_type_news_ids_dict(self):
        if not bool(self.news_type_news_ids_dict_local):
            self.news_type_news_ids_dict_local = pickle.loads(self.rCon.get(self.news_type_news_ids))
            if not len(self.news_type_news_ids_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_type_news_ids)
        return self.news_type_news_ids_dict_local

    def word_id_news_ids_dict(self):
        if not bool(self.word_id_news_ids_dict_local):
            self.word_id_news_ids_dict_local = pickle.loads(self.rCon.get(self.word_id_news_ids))
            if not len(self.word_id_news_ids_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.word_id_news_ids)
        return self.word_id_news_ids_dict_local


    
    def load_data_into_key(self, key, data):
        return self.rCon.set(key,data)
    
    def load_data_into_hash(self, field, key, data):
        return self.rCon.hset(field, key, data)

    def get_data_from_hash(self, field, key):
        return self.rCon.hget(field, key)

    def get_data_from_key(self, key):
        return self.rCon.get(key) 

    def rpush_data_into_list(self, list, message):
        self.rCon.rpush(list, message)

    def lpop_data_from_list(self, list):
        return self.rCon.lpop(list)        

        



