
import redis
import logging
import pickle



class RedisCache:

    user_id_protrait = 'user_id_portrait_dict'


    def __init__(self, host='localhost', port=6379, db=0):
        logging.info('Initial RedisCache ...')
        # Initial connection to Redis
        logging.info('Connect to Redis %s:%s ...', host, port)
        self.rCon = redis.Redis(host=host, port=port, db=db)


    def connection_status(self):
        return self.rCon.client_list()

    

    def get_user_portrait(self, user_id):
        return self.rCon.hget(self.user_id_protrait, user_id)
    
    def save_user_portrait(self, user_id, user_portrait):
        return self.rCon.hset(self.user_id_protrait, user_id, user_portrait)

    
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

        



