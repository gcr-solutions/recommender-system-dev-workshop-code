
import redis
import logging



class RedisCache:

    def __init__(self, host='localhost', port=6379, db=0):
        logging.info('Initial RedisCache ...')
        # Initial connection to Redis
        logging.info('Connect to Redis %s:%s ...', host, port)
        self.rCon = redis.Redis(host=host, port=port, db=db, health_check_interval=30)

    def connection_status(self):
        return self.rCon.client_list()

    
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

    def read_stream_message_block(self, stream_name):
        return self.rCon.xread({stream_name: '$'}, None, 0)

    def read_stream_message(self, stream_name):
        return self.rCon.xread({stream_name: 0})

        



