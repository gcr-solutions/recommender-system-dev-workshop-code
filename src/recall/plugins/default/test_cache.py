import client
import pickle
import logging
import os
import json

logging.basicConfig(level=logging.DEBUG)
rCache = client.RedisCache(host='localhost', port=6379)
test_data = {
    'name': 'test_data',
    'data': [
        {
            'key': 'key1',
            'value': 'value1'
        },
        {
            'key': 'key2',
            'value': 'value2'
        }
    ]
}
pickle_file = open('test_data.pickle', 'wb')
pickle_file.write(pickle.dumps(test_data))
pickle_file.close()


def test_load_data_into_key():
    """
    Test load_data_into_key()
    """
    logging.info('Testing load_data_into_key()')
    file = open('test_data.pickle', 'rb')
    data = file.read()
    rCache.load_data_into_key(rCache.news_id_word_ids, data)
    logging.info('test_data name -> %s', rCache.news_id_word_ids_dict()['name'])
    assert rCache.news_id_word_ids_dict()['name'] == 'test_data', "Name should be 'test_data'"
    assert len(rCache.news_id_word_ids_dict()['data']) == 2, "Length of data should be 2"
    assert rCache.news_id_word_ids_dict()['data'][0]['key'] == 'key1', "key 1 of data should be key 1"
    logging.info('Testing load_data_into_key() was passed')


def test_load_data_into_hash():
    """
    Test test_load_data_into_hash()
    """
    logging.info('Testing test_load_data_into_hash()')
    rCache.load_data_into_hash('test_field','test_key', json.dumps(test_data).encode('utf-8'))
    data = json.loads(rCache.get_data_from_hash('test_field','test_key').decode('utf-8'))
    assert data['name'] == 'test_data', "Name should be 'test_data'"
    assert len(data['data']) == 2, "Length of data should be 2"
    assert data['data'][0]['key'] == 'key1', "key 1 of data should be key 1"
    logging.info('Testing test_load_data_into_hash() was passed')
    




if __name__ == '__main__':
    test_load_data_into_key()
    test_load_data_into_hash()
    os.remove('test_data.pickle')
    print('Everything passed')