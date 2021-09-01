
import redis
import logging

class RedisCache:

    def __init__(self, host='localhost', port=6379, db=0):
        logging.info('Initial RedisCache ...')
        # Initial connection to Redis
        logging.info('Connect to Redis %s:%s ...', host, port)
        self.rCon = redis.Redis(host=host, port=port, db=db)

    def connection_status(self):
        return self.rCon.client_list()

    def lpop_data_from_list(self, list):
        return self.rCon.lpop(list)  

    def get_data_from_hash(self, field, key):
        return self.rCon.hget(field, key) 

    def load_data_into_hash(self, field, key, data):
        return self.rCon.hset(field, key, data)                            

        



