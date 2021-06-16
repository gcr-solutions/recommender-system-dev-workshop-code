import pandas as pd
import boto3
import numpy as np
import os
import glob
from dglke import train as dglke_train
s3client = boto3.client('s3')
# Bucket = 'autorec-1'
class Kg:
    #def __init__(self, kg_folder=None, input_bucket=None, output_bucket=None):
    def __init__(self, env=None):
        self.load_path(env)
        self.entity_to_idx = {} # 记录全部实体（通用+行业）
        self.idx_to_entity = []
        self.relation_to_idx = {}
        self.idx_to_relation = []
        self.entity_industry = set() # 记录行业实体
        self.p = []
        if self.kg_folder != None:
            self.load_file()
            # self.load_file(self.kg_folder, self.input_bucket)
    def load_path(self, env):
        self.kg_folder = env['GRAPH_BUCKET']
        self.kg_dbpedia_key = env['KG_DBPEDIA_KEY'] 
        self.kg_entity_key = env['KG_ENTITY_KEY']
        self.kg_relation_key = env['KG_RELATION_KEY']
        self.kg_dbpedia_train_key = env['KG_DBPEDIA_TRAIN_KEY'] 
        self.kg_entity_train_key = env['KG_ENTITY_TRAIN_KEY']
        self.kg_relation_train_key = env['KG_RELATION_TRAIN_KEY']
        self.kg_entity_industry_key = env['KG_ENTITY_INDUSTRY_KEY']
        self.data_input_key = env['DATA_INPUT_KEY']
        self.train_output_key = env['TRAIN_OUTPUT_KEY']
    def check_parent_dir(self, current_parent, complete_dir):
        dir_split = complete_dir.split('/')
        if len(dir_split) == 1:
            if len(dir_split[0].split('.')) == 1:
                os.makedirs(os.path.join(current_parent,dir_split[0]), exist_ok=True)
            return
        else:
            if not os.path.exists(os.path.join(current_parent,dir_split[0])):
                os.makedirs(os.path.join(current_parent,dir_split[0]), exist_ok=True)
#             print("current {} dir_split[0] {} dir_split[1:0] {}".format(current_parent, dir_split[0], dir_split[1:]))
            self.check_parent_dir(os.path.join(current_parent,dir_split[0]), '/'.join(dir_split[1:]))
    def load_file(self):
        # 加载实体列表
        if not os.path.exists(self.kg_folder):
            os.makedirs(self.kg_folder)
        if not os.path.exists(self.kg_dbpedia_train_key):
            self.check_parent_dir('.', os.path.join(self.kg_folder, self.kg_dbpedia_train_key))
            print("load file: {}".format(os.path.join(self.kg_folder ,self.kg_dbpedia_train_key)))
            s3client.download_file(self.kg_folder, self.kg_dbpedia_train_key, os.path.join(self.kg_folder ,self.kg_dbpedia_train_key))
        if not os.path.exists(self.kg_dbpedia_key):
            self.check_parent_dir('.', os.path.join(self.kg_folder, self.kg_dbpedia_key))
            print("load file: {}".format(os.path.join(self.kg_folder ,self.kg_dbpedia_key)))
            s3client.download_file(self.kg_folder, self.kg_dbpedia_key, os.path.join(self.kg_folder ,self.kg_dbpedia_key))
            # s3client.download_file("sagemaker-us-east-1-002224604296", "recsys_ml_pipeline/model/kg_dbpedia.txt", os.path.join("sagemaker-us-east-1-002224604296","recsys_ml_pipeline/model/kg_dbpedia.txt"))
        if not os.path.exists(self.kg_entity_key):
            self.check_parent_dir('.', os.path.join(self.kg_folder, self.kg_entity_key))
            print("load file: {}".format(os.path.join(self.kg_folder, self.kg_entity_key)))
            s3client.download_file(self.kg_folder, self.kg_entity_key, os.path.join(self.kg_folder ,self.kg_entity_key))
        if not os.path.exists(self.kg_entity_train_key):
            self.check_parent_dir('.', os.path.join(self.kg_folder, self.kg_entity_train_key))
            print("load file: {}".format(os.path.join(self.kg_folder, self.kg_entity_train_key)))
            s3client.download_file(self.kg_folder, self.kg_entity_train_key, os.path.join(self.kg_folder ,self.kg_entity_train_key))
        entities = pd.read_csv(os.path.join(self.kg_folder, self.kg_entity_key), header=None)
        for r in zip(entities[0], entities[1]):
            self.entity_to_idx[str(r[1]).strip()] = r[0]
            self.idx_to_entity.append(str(r[1]).strip())
        # 加载关系三元组
        if not os.path.exists(self.kg_relation_key):
            # self.check_parent_dir(self.kg_folder, self.kg_relation_key)
            self.check_parent_dir('.', os.path.join(self.kg_folder, self.kg_relation_key))
            print("load file: {}".format(os.path.join(self.kg_folder, self.kg_relation_key)))
            s3client.download_file(self.kg_folder, self.kg_relation_key, os.path.join(self.kg_folder ,self.kg_relation_key))
        if not os.path.exists(self.kg_relation_train_key):
            # self.check_parent_dir(self.kg_folder, self.kg_relation_key)
            self.check_parent_dir('.', os.path.join(self.kg_folder, self.kg_relation_train_key))
            print("load file: {}".format(os.path.join(self.kg_folder, self.kg_relation_train_key)))
            s3client.download_file(self.kg_folder, self.kg_relation_train_key, os.path.join(self.kg_folder ,self.kg_relation_train_key)) 
        relations = pd.read_csv(os.path.join(self.kg_folder, self.kg_relation_key), header=None)
        for r in zip(relations[0], relations[1]):
            self.relation_to_idx[str(r[1]).strip()] = r[0]
            self.idx_to_relation.append(str(r[1]).strip())
        # 加载行业专属实体列表
        if not os.path.exists(self.kg_entity_industry_key):
            # self.check_parent_dir(self.kg_folder, self.kg_entity_industry_key)
            self.check_parent_dir('.', os.path.join(self.kg_folder, self.kg_entity_industry_key))
            print("load file: {}".format(os.path.join(self.kg_folder, self.kg_entity_industry_key)))
            s3client.download_file(self.kg_folder, self.kg_entity_industry_key, os.path.join(self.kg_folder ,self.kg_entity_industry_key))
        with open(os.path.join(self.kg_folder, self.kg_entity_industry_key), 'r') as f:
            for word in f:
                self.entity_industry.add(word.strip())                
        # if not os.path.exists(kg_folder + '/kg_dbpedia.txt'):
        #     s3client.download_file(Bucket, 'kg_dbpedia.txt', kg_folder + '/kg_dbpedia.txt')
        # if not os.path.exists(kg_folder + '/entities_dbpedia.dict'):
        #     s3client.download_file(Bucket, 'entities_dbpedia.dict', kg_folder + '/entities_dbpedia.dict')
        # entities = pd.read_csv(kg_folder + '/entities_dbpedia.dict', header=None)
        # for r in zip(entities[0], entities[1]):
        #     self.entity_to_idx[str(r[1]).strip()] = r[0]
        #     self.idx_to_entity.append(str(r[1]).strip())
        # 加载关系三元组
        # if not os.path.exists(kg_folder + '/relations_dbpedia.dict'):
        #     s3client.download_file(Bucket, 'relations_dbpedia.dict', kg_folder + '/relations_dbpedia.dict')
        # relations = pd.read_csv(kg_folder + '/relations_dbpedia.dict', header=None)
        # for r in zip(relations[0], relations[1]):
        #     self.relation_to_idx[str(r[1]).strip()] = r[0]
        #     self.idx_to_relation.append(str(r[1]).strip())
        # 加载行业专属实体列表
        # if not os.path.exists(kg_folder + '/entity_industry.txt'):
        #     s3client.download_file(Bucket, 'entity_industry.txt', kg_folder + '/entity_industry.txt')
        # with open(kg_folder + '/entity_industry.txt', 'r') as f:
        #     for word in f:
        #         self.entity_industry.add(word.strip())                
    # def load_file(self, kg_folder):
    #     # 加载实体列表
    #     if not os.path.exists(kg_folder):
    #         os.makedirs(kg_folder)
    #     if not os.path.exists(kg_folder + '/kg_dbpedia.txt'):
    #         s3client.download_file(Bucket, 'kg_dbpedia.txt', kg_folder + '/kg_dbpedia.txt')
    #     if not os.path.exists(kg_folder + '/entities_dbpedia.dict'):
    #         s3client.download_file(Bucket, 'entities_dbpedia.dict', kg_folder + '/entities_dbpedia.dict')
    #     entities = pd.read_csv(kg_folder + '/entities_dbpedia.dict', header=None)
    #     for r in zip(entities[0], entities[1]):
    #         self.entity_to_idx[r[1]] = r[0]
    #         self.idx_to_entity.append(r[1])
    #     # 加载关系三元组
    #     if not os.path.exists(kg_folder + '/relations_dbpedia.dict'):
    #         s3client.download_file(Bucket, 'relations_dbpedia.dict', kg_folder + '/relations_dbpedia.dict')
    #     relations = pd.read_csv(kg_folder + '/relations_dbpedia.dict', header=None)
    #     for r in zip(relations[0], relations[1]):
    #         self.relation_to_idx[r[1]] = r[0]
    #         self.idx_to_relation.append(r[1])
    #     # 加载行业专属实体列表
    #     if not os.path.exists(kg_folder + '/entity_industry.txt'):
    #         s3client.download_file(Bucket, 'entity_industry.txt', kg_folder + '/entity_industry.txt')
    #     with open(kg_folder + '/entity_industry.txt', 'r') as f:
    #         for word in f:
    #             self.entity_industry.add(word.strip())
    def add_entity(self, entity_name, industry = False):
        # 如果待加入实体不在实体列表中，则添加。如果industry为True，则同时记录为行业实体
        if entity_name not in self.entity_to_idx:
            self.entity_to_idx[entity_name] = len(self.entity_to_idx)
            self.idx_to_entity.append(entity_name)
            if industry:
                self.entity_industry.add(entity_name)
    def add_relation(self, head, relation, tail):
        # 判断relation是否在关系列表中
        if relation not in self.relation_to_idx:
            self.relation_to_idx[relation] = len(self.relation_to_idx)
            self.idx_to_relation.append(relation)
        relation_id = self.relation_to_idx[relation]
        # 判断head是否在实体列表中
        if head not in self.entity_to_idx:
            self.add_entity(head)
        head_id = self.entity_to_idx[head]
        # 判断tail是否在实体列表中
        if tail not in self.entity_to_idx:
            self.add_entity(tail)
        tail_id = self.entity_to_idx[tail]
        pair = str(head_id) + '\t' +str(relation_id) + '\t' +str(tail_id) + '\n'
        self.p.append(pair)
    def save(self):
        entities_dbpedia=pd.DataFrame([[v,k] for k,v in self.entity_to_idx.items()])
        relations_dbpedia=pd.DataFrame([[v,k] for k,v in self.relation_to_idx.items()])
        entities_dbpedia.to_csv(self.kg_folder + '/entities_dbpedia.dict', header=None,index=None)
        relations_dbpedia.to_csv(self.kg_folder + '/relations_dbpedia.dict', header=None,index=None)
        with open(self.kg_folder + '/entity_industry.txt', 'w') as f:
            for k in self.entity_industry:
                f.write(k + '\n')
        with open(self.kg_folder + '/kg_dbpedia.txt', 'a') as f:
            for k in self.p:
                f.write(k)
#     def train(self, output_dir = 'kg_embedding', hidden_dim=128, max_step=320000):
    def train(self, output_dir = '/opt/ml/model', hidden_dim=128, max_step=200, method='RotatE', upload_context=True):
        self.check_parent_dir('.',self.train_output_key)
        dglke_train.main(['--dataset',self.kg_folder,
                  '--model_name', method,
                  '--gamma','19.9',
                  '--lr', '0.25',
                  '--max_step',str(max_step),
                  '--log_interval',str(max_step//100),
                  '--batch_size_eval','1000',
                  '--hidden_dim', str(hidden_dim//2), # RotatE模型传入的是1/2 hidden_dim的
                  '-adv',
                  '--regularization_coef','1.00E-09',
                  '--gpu','0',
                  '--double_ent',
                  '--mix_cpu_gpu',
                  '--save_path',self.train_output_key,
                  '--data_path',self.kg_folder,
                  '--format','udd_hrt',
                  '--data_files',self.kg_entity_train_key,self.kg_relation_train_key,self.kg_dbpedia_train_key,
                  '--neg_sample_size_eval','10000'])
        # dglke_train.main(['--dataset','kg',
        #           #'--model_name','RotatE'
        #           '--gamma','19.9',
        #           '--lr', '0.25',
        #           '--max_step',str(max_step),
        #           '--log_interval',str(max_step//100),
        #           '--batch_size_eval','1000',
        #           '--hidden_dim', str(hidden_dim//2), # RotatE模型传入的是1/2 hidden_dim的
        #           '-adv',
        #           '--regularization_coef','1.00E-09',
        #           '--gpu','0',
        #           '--double_ent',
        #           '--mix_cpu_gpu',
        #           '--save_path',output_dir,
        #           '--data_path',self.kg_folder,
        #           '--format','udd_hrt',
        #           '--data_files','entities_dbpedia.dict','relations_dbpedia.dict','kg_dbpedia.txt',
        #           '--neg_sample_size_eval','10000'])
        print("finish training!!")
        print("start to generate context numpy")
        generate_entity_name = self.kg_folder+'_'+method+'_entity.npy'
        generate_context_name = self.kg_folder+'_'+method+'_context.npy'
        generate_relation_name = self.kg_folder+'_'+method+'_relation.npy'
        upload_entity_name = "dkn_entity_embedding.npy"
        upload_context_name = "dkn_context_embedding.npy"
        upload_relation_name = "dkn_relation_embedding.npy"
        kg_embedding = np.load(os.path.join(self.train_output_key, generate_entity_name))
        context_embeddings = np.zeros([kg_embedding.shape[0], hidden_dim], dtype="float32")
        entity2neighbor_map = dict()
        with open(os.path.join(self.kg_folder ,self.kg_dbpedia_train_key)) as f: # 修改‘kg/kg_dbpedia.txt’文件路径
            for line in f:
                line = line.strip().split("\t")
                head, _, tail = line
                head = self.idx_to_entity[int(head)] # 修改kg.idx_to_entity
                tail = self.idx_to_entity[int(tail)]
                if head in entity2neighbor_map:
                    entity2neighbor_map[head].append(tail)
                else:
                    entity2neighbor_map[head] = [tail]
                if tail in entity2neighbor_map:
                    entity2neighbor_map[tail].append(head)
                else:
                    entity2neighbor_map[tail] = [head]
        for entity, index in self.entity_to_idx.items(): # 修改kg.entity_to_idx
            if entity in entity2neighbor_map:
                context_full_entities = [self.entity_to_idx[row] for row in entity2neighbor_map[entity]]
                context_embeddings[index] = np.average(kg_embedding[context_full_entities], axis=0)
                               
#         np.save(‘kg_embedding/kg_RotatE_context.npy’, context_embeddings)
        np.save(os.path.join(self.train_output_key, generate_context_name), context_embeddings)
                               
        if self.train_output_key != None:
            print("upload to {}".format(self.train_output_key))
            s3client.upload_file(os.path.join(self.train_output_key, generate_entity_name), self.kg_folder, os.path.join(self.train_output_key, upload_entity_name))
            s3client.upload_file(os.path.join(self.train_output_key, generate_relation_name), self.kg_folder, os.path.join(self.train_output_key, upload_relation_name))
            if upload_context == True:
                s3client.upload_file(os.path.join(self.train_output_key, generate_context_name), self.kg_folder, os.path.join(self.train_output_key, upload_context_name))
#             for name in glob.glob(os.path.join(self.train_output_key,'*.npy')):
#                 print("upload {}".format(name))
#                 s3client.upload_file(name, self.kg_folder, os.path.join(self.train_output_key,name.split('/')[-1]))
