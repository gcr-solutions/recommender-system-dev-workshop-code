import redis
import logging
import pickle



class RedisCache:

    news_type_news_ids = 'news_type_news_ids_dict'

    def __init__(self, host='localhost', port=6379, db=0):
        logging.info('Initial RedisCache ...')
        # Initial connection to Redis
        logging.info('Connect to Redis %s:%s ...', host, port)
        self.rCon = redis.Redis(host=host, port=port, db=db)

        self.news_type_news_ids_dict_local = {}


    def connection_status(self):
        return self.rCon.client_list()

    def load_data_into_hash(self, field, key, data):
        return self.rCon.hset(field, key, data)

    def get_data_from_hash(self, field, key):
        return self.rCon.hget(field, key) 

    def news_type_news_ids_dict(self):
        if not bool(self.news_type_news_ids_dict_local):
            self.news_type_news_ids_dict_local = pickle.loads(self.rCon.get(self.news_type_news_ids))
            if not len(self.news_type_news_ids_dict_local)>0:
                logging.error('Failed to load pickle - %s from Redis.?!', self.news_type_news_ids)
        return self.news_type_news_ids_dict_local  

    def get_zrange(self, field, start, end):
        return self.rCon.zrange(field, start, end) 

    def get_zcard(self, field):
        return self.rCon.zcard(field)

    def zadd(self, field, data):
        self.rCon.zadd(field, data) 

    def incr(self, key):
        return self.incr(key)

        



