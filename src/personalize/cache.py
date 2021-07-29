# import redis
# import logging
#
#
# class RedisCache:
#
#     def __init__(self, host='localhost', port=6379, db=0):
#         logging.info('Initial RedisCache ...')
#         # Initial connection to Redis
#         logging.info('Connect to Redis %s:%s ...', host, port)
#         self.rCon = redis.Redis(host=host, port=port, db=db)
#
#     def connection_status(self):
#         return self.rCon.client_list()
#
#     def lpop_data_from_list(self, list):
#         return self.rCon.lpop(list)
#
#     def read_stream_message_block(self, stream_name):
#         return self.rCon.xread({stream_name: '$'}, None, 0)
#
#     def read_stream_message(self, stream_name):
#         return self.rCon.xread({stream_name: 0})
#
#
#
#
#
