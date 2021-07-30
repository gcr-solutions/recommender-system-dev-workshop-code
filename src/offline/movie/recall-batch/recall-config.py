import pickle

recall_config = {}
# 可配置的参数
# 每种方法召回的物品数目
recall_config['mt_topn'] = {}
recall_config['mt_topn']['category'] = 10
recall_config['mt_topn']['director'] = 10
recall_config['mt_topn']['actor'] = 10
recall_config['mt_topn']['language'] = 10
recall_config['mt_topn']['level'] = 10
recall_config['mt_topn']['year'] = 10
recall_config['mt_topn']['review'] = 10
recall_config['mt_topn']['photo'] = 10
recall_config['mt_topn']['portrait_category'] = 10
recall_config['mt_topn']['portrait_director'] = 10
recall_config['mt_topn']['portrait_actor'] = 10
recall_config['mt_topn']['portrait_language'] = 10
recall_config['mt_topn']['portrait_ub'] = 10

# 可学习的参数
# 每种产生rank的方法的打分系数，未来通过反馈的ctr进行学习
recall_config['pos_weights'] = {}
recall_config['pos_weights']['category'] = {}
recall_config['pos_weights']['category']['w'] = 0.5
recall_config['pos_weights']['category']['b'] = 0.2
recall_config['pos_weights']['director'] = {}
recall_config['pos_weights']['director']['w'] = 0.5
recall_config['pos_weights']['director']['b'] = 0.2
recall_config['pos_weights']['actor'] = {}
recall_config['pos_weights']['actor']['w'] = 0.5
recall_config['pos_weights']['actor']['b'] = 0.2
recall_config['pos_weights']['language'] = {}
recall_config['pos_weights']['language']['w'] = 0.5
recall_config['pos_weights']['language']['b'] = 0.2
recall_config['pos_weights']['level'] = {}
recall_config['pos_weights']['level']['w'] = 0.5
recall_config['pos_weights']['level']['b'] = 0.2
recall_config['pos_weights']['year'] = {}
recall_config['pos_weights']['year']['w'] = 0.5
recall_config['pos_weights']['year']['b'] = 0.2
recall_config['pos_weights']['portrait_category'] = {}
recall_config['pos_weights']['portrait_category']['w'] = 0.5
recall_config['pos_weights']['portrait_category']['b'] = 0.2
recall_config['pos_weights']['portrait_director'] = {}
recall_config['pos_weights']['portrait_director']['w'] = 0.5
recall_config['pos_weights']['portrait_director']['b'] = 0.2
recall_config['pos_weights']['portrait_actor'] = {}
recall_config['pos_weights']['portrait_actor']['w'] = 0.5
recall_config['pos_weights']['portrait_actor']['b'] = 0.2
recall_config['pos_weights']['portrait_language'] = {}
recall_config['pos_weights']['portrait_language']['w'] = 0.5
recall_config['pos_weights']['portrait_language']['b'] = 0.2

# 每种方法的权重, 未来根据反馈的ctr更新：加权平均
method_weights = {}
method_weights['category'] = 1.0
method_weights['director'] = 1.0
method_weights['actor'] = 1.0
method_weights['language'] = 1.0
method_weights['level'] = 1.0
method_weights['year'] = 1.0
method_weights['portrait_category'] = 1.0
method_weights['portrait_director'] = 1.0
method_weights['portrait_actor'] = 1.0
method_weights['portrait_language'] = 1.0
method_weights['portrait_ub'] = 1.0
recall_config['mt_weights'] = method_weights

# 不同策略的方法
popularity_method_list = ['category', 'director',
                          'actor', 'language', 'level', 'year']
portrait_method_list = ['category', 'director',
                          'actor', 'language']
recall_config['pop_mt_list'] = popularity_method_list
recall_config['portrait_mt_list'] = portrait_method_list

file_name = 'recall_config.pickle'
output_file = open(file_name, 'wb')
pickle.dump(recall_config, output_file)
output_file.close()