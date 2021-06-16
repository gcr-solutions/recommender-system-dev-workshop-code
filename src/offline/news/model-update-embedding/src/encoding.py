import boto3
import numpy as np
import json
import re
import os
import sys
print("sys path is {}".format(sys.path))
from fastHan import FastHan
import marisa_trie
s3client = boto3.client('s3')
# Bucket = 'autorec-1'

class Vocab:
    def __init__(self, Bucket, vocab_key, vocab_file = None):
        self.token_to_idx = {}
        if not os.path.exists(Bucket):
            os.makedirs(Bucket)
        if vocab_file == None:
            if not os.path.exists(vocab_key):
                self.check_parent_dir('.', os.path.join(Bucket,vocab_key))
                s3client.download_file(Bucket, vocab_key, os.path.join(Bucket, vocab_key))
            vocab_file = os.path.join(Bucket, vocab_key)
        self.idx_to_token = ['<unk>'] + json.load(open(vocab_file,'r'))
        for i, token in enumerate(self.idx_to_token):
            self.token_to_idx[token] = i
        self.unk = 0
    def check_parent_dir(self, current_parent, complete_dir):
        dir_split = complete_dir.split('/')
        if len(dir_split) == 1:
            if len(dir_split[0].split('.')) == 1:
                os.makedirs(os.path.join(current_parent,dir_split[0]))
            return
        else:
            if not os.path.exists(os.path.join(current_parent,dir_split[0])):
                os.makedirs(os.path.join(current_parent,dir_split[0]))
            self.check_parent_dir(os.path.join(current_parent,dir_split[0]), '/'.join(dir_split[1:]))
    def __len__(self):
        return len(self.idx_to_token)

    def __getitem__(self, tokens):
        if not isinstance(tokens, (list, tuple)):
            return self.token_to_idx.get(tokens, self.unk)
        return [self.__getitem__(token) for token in tokens]

    def to_tokens(self, indices):
        if not isinstance(indices, (list, tuple)):
            return self.idx_to_token[indices]
        return [self.idx_to_token[index] for index in indices]
    
class encoding:
    # def __init__(self, kg, input_bucket, output_bucket=None):
    def __init__(self, kg, env):
        self.kg = kg
        self.bert_entity_to_idx = {}
        self.bert_idx_to_entity = {}
        # self.input_bucket = input_bucket
        # self.output_bucket = output_bucket
        self.trie = marisa_trie.Trie(list(kg.entity_industry))
        self.vocab = Vocab(env['GRAPH_BUCKET'], env['KG_VOCAB_KEY'])
        self.model=FastHan()
    def __getitem__(self, text):
        seg, ner_gen, ner_indu, ner_bert = self.word_parser(text)
        return self.get_encoding(seg, ner_gen, ner_indu, ner_bert)
    def get_industry_entities(self, sentence):
        entities = []
        i = 0
        while i < len(sentence):
            for j in range(i+1, len(sentence)+1):
#                 print("try to match sentence[{}:{}]: {}".format(i,j,sentence[i:j]))
                keyword_prefix = self.trie.keys(''.join(sentence[i:j]))
                if len(keyword_prefix) == 0:
                    if ''.join(sentence[i:j-1]) in self.trie:
#                         print("During found {}".format(sentence[i:j-1]))
                        entities.append((i, j-1))
                    if j-1 == i:
                        i = j
                    else:
                        i = j-1
                    break
                if j == len(sentence):
                    if ''.join(sentence[i:j]) in self.trie:
#                         print("Last found {}".format(sentence[i:j-1]))
                        entities.append((i, j))
                    i = j
                    break
        return entities

    def finditer(self, string_candidate, string):
        last_p = -1
#         print("string candiate is {}".format(string_candidate))
#         print("string is {}".format(string))
        sub_string = string_candidate
        while len(string):
#             print("sub_string is {}".format(sub_string))
            if sub_string in string:
                p = string.index(sub_string)
                string = string[p+1:]
                p = p + last_p +1
                last_p = p
                yield (p, last_p+len(sub_string))
            else:
                break

    def word_parser(self, text):
        seg = [str(word).strip() for word in self.model(text)[0] if len(str(word).strip())!=0]
        ner_pre = self.model(text, target="NER")[0]
#         print("seg is {} ner_pre from fastHan is {}".format(seg, ner_pre))
        ner_gen = []
        word_pos = [0]
        for word in seg:
            word_pos.append(len(word) + word_pos[-1])
#         print("ner pre is {} with type {}".format(ner_pre, type(ner_pre)))
        for n in ner_pre:
#             n = str(n).replace('*','\*')
#             print("loop {}".format(n))
#             for j in re.finditer('%r'%n, ''.join(seg)):
#             for j in self.finditer('%s'%n, ''.join(seg)):
            for j in self.finditer(n[0], ''.join(seg)):
                start, end = None, None
                for i in range(len(word_pos)-1):
                    if j[0] == word_pos[i]:
                        start = i
                    if j[1] == word_pos[i+1]:
                        end = i+1
                if start!=None and end != None:
                    ner_gen.append((start, end))
        ner_indu = self.get_industry_entities(seg)
        ner_bert = ner_gen
        return seg, ner_gen, ner_indu, ner_bert
    # def word_parser(self, text):
    #     seg = [str(word).strip() for word in self.model(text)[0] if len(str(word).strip())!=0]
    #     ner_pre = self.model(text, target="NER")[0]
    #     ner_gen = []
    #     word_pos = [0]
    #     for word in seg:
    #         word_pos.append(len(word) + word_pos[-1])
    #     for n in ner_pre:
    #         for j in re.finditer(str(n), ''.join(seg)):
    #             start, end = None, None
    #             for i in range(len(word_pos)-1):
    #                 if j.span()[0] == word_pos[i]:
    #                     start = i
    #                 if j.span()[1] == word_pos[i+1]:
    #                     end = i+1
    #             if start!=None and end != None:
    #                 ner_gen.append((start, end))
    #     ner_indu = self.get_industry_entities(seg)
    #     return seg, ner_gen, ner_indu
    def get_encoding(self, seg, ner_gen, ner_indu, ner_bert):
#         print("seg is {}, ner_gen/ner_bert is {} and ner_indu is {}".format(seg, ner_gen, ner_indu))
        max_len = 16
        word_encoding = self.vocab[seg]
        word_encoding = word_encoding[:max_len] + [0] * (max_len - len(word_encoding))
        # 精确匹配到的行业实体
        entity_encoding = [0] * max_len

        for n in ner_indu:
            n_s = ''
            for _ in range(n[0], n[1]):
                n_s += seg[_]
            e_id = self.kg.entity_to_idx[n_s]
            for _ in range(n[0], n[1]):
                if _ < max_len:
                    entity_encoding[_] = e_id

        # NER模型得到的实体            
        flag = [0] * max_len
        for n in ner_gen:
            n_s = ''
            for _ in range(n[0], n[1]):
                n_s += seg[_]
            if n_s in self.kg.entity_to_idx:
                e_id = self.kg.entity_to_idx[n_s]
                for _ in range(n[0], n[1]):
                    if _ < max_len:
                        flag[_] = e_id

        # 合并两种不同方法获取到的实体
        for j in range(len(entity_encoding)):
            if entity_encoding[j] == 0 and flag[j] != 0:
                entity_encoding[j] = flag[j]
        
        # create bert encoding on the fly: recall entity-index
        bert_entity = [0] * max_len
        for n in ner_bert:
            n_s = ''
            for _ in range(n[0], n[1]):
                n_s += seg[_]
#             print("found bert entity {}".format(n_s))
            e_id = 0
            if n_s in self.bert_entity_to_idx:
                e_id = self.bert_entity_to_idx[n_s]
            else:
                new_len = len(self.bert_entity_to_idx) + 1
                self.bert_entity_to_idx[n_s] = new_len
                self.bert_idx_to_entity[new_len] = n_s
                e_id = new_len
            for _ in range(n[0], n[1]):
                if _ < max_len:
                    bert_entity[_] = e_id

        return word_encoding, entity_encoding, bert_entity
