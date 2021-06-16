
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

    def load_data_into_stream(self, stream_name, data):
        return self.rCon.xadd(stream_name, data, maxlen=1, approximate=False)       

        



