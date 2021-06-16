import sys
import numpy as np
import tensorflow as tf
from sklearn.metrics import roc_auc_score
import pandas as pd
from collections import namedtuple
import subprocess
import argparse
import os
import json
import shutil
import glob
from datetime import date, timedelta

from tempfile import TemporaryDirectory

#################### CMD Arguments ####################
FLAGS = tf.app.flags.FLAGS

# model param
tf.app.flags.DEFINE_boolean(
    "transform", False, "whether to transform entity embeddings")
tf.app.flags.DEFINE_boolean("use_context", False,
                            "whether to transform context embeddings")
tf.app.flags.DEFINE_boolean("use_entity", True,
                            "whether to transform entity embeddings")
tf.app.flags.DEFINE_integer("max_click_history", 8,
                            "number of sampled click history for each user")
tf.app.flags.DEFINE_integer(
    "n_filters", 128, "number of filters for each size in KCNN")
tf.app.flags.DEFINE_list(
    'filter_sizes', [1, 2], 'list of filter sizes, e.g., --filter_sizes 2 3')
tf.app.flags.DEFINE_float('l2_weight', 0.001, 'weight of l2 regularization')
tf.app.flags.DEFINE_string('attention_activation', 'relu',
                           'activation method for attention module')
tf.app.flags.DEFINE_string('KGE', 'TransE',
                           'knowledge graph embedding method, please ensure that the specified input file exists')
tf.app.flags.DEFINE_integer('entity_dim', 128,
                            'dimension of entity embeddings, please ensure that the specified input file exists')
tf.app.flags.DEFINE_integer('word_dim', 300,
                            'dimension of word embeddings, please ensure that the specified input file exists')
tf.app.flags.DEFINE_integer('max_title_length', 16,
                            'maximum length of news titles, should be in accordance with the input datasets')
tf.app.flags.DEFINE_integer('attention_layer_sizes', 100,
                            'layer sizes of attention module')
tf.app.flags.DEFINE_list('layer_sizes', [100],
                            'layer size for final prediction score layer')
tf.app.flags.DEFINE_list('activation', ['sigmoid'],
                           'activation method for attention module')

# training param
tf.app.flags.DEFINE_integer("perform_shuffle", 0, "perform shuffle data")
tf.app.flags.DEFINE_integer("num_epochs", 10, "Number of epochs")
tf.app.flags.DEFINE_integer("batch_size", 128, "Number of batch size")
tf.app.flags.DEFINE_integer("log_steps", 1000, "save summary every steps")
tf.app.flags.DEFINE_float("learning_rate", 0.001, "learning rate")
tf.app.flags.DEFINE_float("embed_l1", 0.00000, "L1 regularization for embeddings")
tf.app.flags.DEFINE_float("layer_l1", 0.00000, "L1 regularization for nn layers")
tf.app.flags.DEFINE_float("embed_l2", 0.00001, "L2 regularization for embeddings")
# tf.app.flags.DEFINE_float("layer_l2", 0.00003, "L2 regularization for nn layers")
tf.app.flags.DEFINE_float("layer_l2", 0.001, "L2 regularization for nn layers")
tf.app.flags.DEFINE_float("cross_l1", 0.00000, "cross L1 regularization")
tf.app.flags.DEFINE_float("cross_l2", 0.00000, "corss L2 regularization")
tf.app.flags.DEFINE_string("loss_type", 'log_loss',
                           "loss type {square_loss, log_loss}")
tf.app.flags.DEFINE_string(
    "optimizer", 'Adam', "optimizer type {Adam, Adagrad, GD, Momentum}")
tf.app.flags.DEFINE_string("data_dir", '', "data dir")
tf.app.flags.DEFINE_string("dt_dir", '', "data dt partition")
tf.app.flags.DEFINE_string("model_dir", '', "model check point dir")
tf.app.flags.DEFINE_string("servable_model_dir", '',
                           "export servable model for TensorFlow Serving")
tf.app.flags.DEFINE_string(
    "task_type", 'train', "task type {train, infer, eval, export}")
tf.app.flags.DEFINE_boolean("clear_existing_model",
                            False, "clear existing model or not")
tf.app.flags.DEFINE_string(
    "checkpointPath", '', "checkpoint path during training ")
tf.app.flags.DEFINE_float(
    "loss_weight", '1.0', "weight for pos sample")
tf.app.flags.DEFINE_list('dropout', [0.0], 'dropout parameters of training stage')

Data = namedtuple('Data', ['size', 'clicked_words',
                           'clicked_entities', 'news_words', 'news_entities', 'labels'])

class DKN(object):
    # def __init__(self, params, feature=None, labels=None, hparams=hparams):
    def __init__(self, params, feature=None, labels=None):
        # prepare train/test data
        # print(params)
        self.train_data = None
        self.test_data = None
        seed = 30
        init_value = 0.1
        self.initializer = tf.random_uniform_initializer(
            -init_value, init_value, seed=seed)
        self.n_filters_total = params["n_filters"] * len(params["filter_sizes"])
        self.reg_params = []  # for computing regularization loss
        self.layer_params = []
        self.embed_params = []
        self.cross_params = []
        self._build_inputs(params, feature, labels)
        # # build raw model
        # self._build_model(params)
        # build ms implement model
        # self.hparams=hparams
        self.params=params
        self._build_ms_model(params)
        # self._build_train(params)

    def _build_inputs(self, params, feature=None, labels=None):
        self.clicked_words = feature["click_words"]
        self.clicked_entities = feature["click_entities"]
        self.news_words = feature["news_words"]
        self.news_entities = feature["news_entities"]
        self.labels = labels
        print("!!!!!!!!!!verify input shape")
        print("!!!!!!!!!!clicked words {}".format(self.clicked_words))
        print("!!!!!!!!!!clicked entities {}".format(self.clicked_entities))
        print("!!!!!!!!!!news words {}".format(self.news_words))
        print("!!!!!!!!!!news entities {}".format(self.news_entities))
    
    def _build_ms_model(self, params):
        with tf.name_scope('embedding'):
            if FLAGS.data_dir == '':
                raw_dir = os.environ.get('SM_CHANNEL_TRAIN')
            else:
                raw_dir = os.path.join(FLAGS.data_dir, 'train')
#             word_embs = np.load(
#                 os.path.join(raw_dir,'word_embeddings_' + str(params["word_dim"]) + '.npy'))
#             entity_embs = np.load(os.path.join(raw_dir,'entity_embeddings_' +
#                                   params["KGE"] + '_' + str(params["entity_dim"]) + '.npy'))
#             # word_embs = np.load(os.path.join(raw_dir, 'word_embeddings.npy'))
#             # entity_embs = np.load(os.path.join(
#             #     raw_dir, 'entity_embeddings.npy'))
#             self.word_embeddings = tf.Variable(
#                 word_embs, trainable=False, dtype=np.float32, name='word')
# #             self.word_embeddings = word_embs
#             self.entity_embeddings = tf.Variable(
#                 entity_embs, trainable=False, dtype=np.float32, name='entity')
#             self.entity_embeddings = entity_embs
#             self.reg_params.append(self.word_embeddings)
#             self.reg_params.append(self.entity_embeddings)
#             print("run here 1!")
#             print(params["use_context"])

            if params["use_context"]:
                print("run here 2.1!")
                context_embs = np.load(os.path.join(raw_dir,'context_embeddings_' +
                                      params["KGE"] + '_' + str(params["entity_dim"]) + '.npy'))
                self.context_embeddings = tf.Variable(
                    context_embs, trainable=False, dtype=np.float32, name='context')
#                 self.reg_params.append(self.context_embeddings)
#                 print("run here 2.2!")

            if params["transform"]:
#                 print("run here 3.1!")
                self.entity_embeddings = tf.layers.dense(
                    self.entity_embeddings, units=params["entity_dim"], activation=tf.nn.tanh, name='transformed_entity',
                    kernel_regularizer=tf.contrib.layers.l2_regularizer(params["l2_weight"]))
#                 print("run here 3.2!")
                if params["use_context"]:
                    print("run here transform context")
                    self.context_embeddings = tf.layers.dense(
                        self.context_embeddings, units=params["entity_dim"], activation=tf.nn.tanh,
                        name='transformed_context', kernel_regularizer=tf.contrib.layers.l2_regularizer(params["l2_weight"]))
#         print("build graph")
        self.logit = tf.reshape(self._build_graph(), [-1])
#         print("build output")
        self.output = tf.sigmoid(self.logit)

    def _build_graph(self):
        params = self.params
        # print("params {}".format(params))
        self.keep_prob_train = 1 - np.array(params["dropout"])
        self.keep_prob_test = np.ones_like(params["dropout"])
        with tf.compat.v1.variable_scope("DKN") as scope:
            logit = self._build_dkn()
            return logit

    def _build_dkn(self):
        """The main function to create DKN's logic.
        
        Returns:
            obj: Prediction score made by the DKN model.
        """
        params = self.params

        click_news_embed_batch, candidate_news_embed_batch = self._build_pair_attention(
            self.news_words,
            self.news_entities,
            self.clicked_words,
            self.clicked_entities,
            self.params,
        )

        nn_input = tf.concat(
            [click_news_embed_batch, candidate_news_embed_batch], axis=1
        )

        dnn_channel_part = 2
        last_layer_size = dnn_channel_part * self.num_filters_total
        layer_idx = 0
        hidden_nn_layers = []
        hidden_nn_layers.append(nn_input)
        with tf.compat.v1.variable_scope(
            "nn_part", initializer=self.initializer
        ) as scope:
            for idx, layer_size in enumerate(params["layer_sizes"]):
                curr_w_nn_layer = tf.compat.v1.get_variable(
                    name="w_nn_layer" + str(layer_idx),
                    shape=[last_layer_size, layer_size],
                    dtype=tf.float32,
                )
                curr_b_nn_layer = tf.compat.v1.get_variable(
                    name="b_nn_layer" + str(layer_idx),
                    shape=[layer_size],
                    dtype=tf.float32,
                )
                curr_hidden_nn_layer = tf.compat.v1.nn.xw_plus_b(
                    hidden_nn_layers[layer_idx], curr_w_nn_layer, curr_b_nn_layer
                )
                # if hparams.enable_BN is True:
                #     curr_hidden_nn_layer = tf.layers.batch_normalization(
                #         curr_hidden_nn_layer,
                #         momentum=0.95,
                #         epsilon=0.0001,
                #         training=self.is_train_stage,
                #     )

                activation = params["activation"][idx]
                # curr_hidden_nn_layer = self._active_layer(
                #     logit=curr_hidden_nn_layer, activation=activation
                # )
                curr_hidden_nn_layer = tf.nn.sigmoid(curr_hidden_nn_layer)
                hidden_nn_layers.append(curr_hidden_nn_layer)
                layer_idx += 1
                last_layer_size = layer_size
#                 self.layer_params.append(curr_w_nn_layer)
#                 self.layer_params.append(curr_b_nn_layer)

            w_nn_output = tf.compat.v1.get_variable(
                name="w_nn_output", shape=[last_layer_size, 1], dtype=tf.float32
            )
            b_nn_output = tf.compat.v1.get_variable(
                name="b_nn_output", shape=[1], dtype=tf.float32
            )
#             self.layer_params.append(w_nn_output)
#             self.layer_params.append(b_nn_output)
            nn_output = tf.compat.v1.nn.xw_plus_b(
                hidden_nn_layers[-1], w_nn_output, b_nn_output
            )
            return nn_output

    def _build_pair_attention(
        self,
        candidate_word_batch,
        candidate_entity_batch,
        click_word_batch,
        click_entity_batch,
        params,
    ):
        """This function learns the candidate news article's embedding and user embedding.
        User embedding is generated from click history and also depends on the candidate news article via attention mechanism.
        Article embedding is generated via KCNN module.
        Args:
            candidate_word_batch (obj): tensor word indices for constructing news article
            candidate_entity_batch (obj): tensor entity values for constructing news article
            click_word_batch (obj): tensor word indices for constructing user clicked history
            click_entity_batch (obj): tensor entity indices for constructing user clicked history
            params (obj): global hyper-parameters
        Returns:
            click_field_embed_final_batch: user embedding
            news_field_embed_final_batch: candidate news article embedding

        """
        doc_size = params["max_title_length"]
        attention_hidden_sizes = params["attention_layer_sizes"]

#         clicked_words = tf.reshape(click_word_batch, shape=[-1, doc_size])
#         clicked_entities = tf.reshape(click_entity_batch, shape=[-1, doc_size])
        
        clicked_words = click_word_batch
        clicked_entities = click_entity_batch

        with tf.compat.v1.variable_scope(
            "attention_net", initializer=self.initializer
        ) as scope:

            # use kims cnn to get conv embedding
            with tf.compat.v1.variable_scope(
                "kcnn", initializer=self.initializer, reuse=tf.compat.v1.AUTO_REUSE
            ) as cnn_scope:
                news_field_embed = self._kims_cnn(
                    candidate_word_batch, candidate_entity_batch, params
                )
                click_field_embed = self._kims_cnn(
                    clicked_words, clicked_entities, params
                )
                click_field_embed = tf.reshape(
                    click_field_embed,
                    shape=[
                        -1,
                        params["max_click_history"],
                        params["n_filters"] * len(params["filter_sizes"]),
                    ],
                )

            avg_strategy = False
            if avg_strategy:
                click_field_embed_final = tf.reduce_mean(
                    click_field_embed, axis=1, keepdims=True
                )
            else:
                news_field_embed = tf.expand_dims(news_field_embed, 1)
                news_field_embed_repeat = tf.add(
                    tf.zeros_like(click_field_embed), news_field_embed
                )
                attention_x = tf.concat(
                    axis=-1, values=[click_field_embed, news_field_embed_repeat]
                )
                attention_x = tf.reshape(
                    attention_x, shape=[-1, self.num_filters_total * 2]
                )
                attention_w = tf.compat.v1.get_variable(
                    name="attention_hidden_w",
                    shape=[self.num_filters_total * 2, attention_hidden_sizes],
                    dtype=tf.float32,
                )
                attention_b = tf.compat.v1.get_variable(
                    name="attention_hidden_b",
                    shape=[attention_hidden_sizes],
                    dtype=tf.float32,
                )
                curr_attention_layer = tf.compat.v1.nn.xw_plus_b(
                    attention_x, attention_w, attention_b
                )

                activation = params["attention_activation"]
                curr_attention_layer = tf.nn.relu(curr_attention_layer)
                attention_output_w = tf.compat.v1.get_variable(
                    name="attention_output_w",
                    shape=[attention_hidden_sizes, 1],
                    dtype=tf.float32,
                )
                attention_output_b = tf.compat.v1.get_variable(
                    name="attention_output_b", shape=[1], dtype=tf.float32
                )
                attention_weight = tf.compat.v1.nn.xw_plus_b(
                    curr_attention_layer, attention_output_w, attention_output_b
                )
                attention_weight = tf.reshape(
                    attention_weight, shape=[-1, params["max_click_history"], 1]
                )
                norm_attention_weight = tf.nn.softmax(attention_weight, axis=1)
                click_field_embed_final = tf.reduce_sum(
                    tf.multiply(click_field_embed, norm_attention_weight),
                    axis=1,
                    keepdims=True,
                )
#                 if attention_w not in self.layer_params:
#                     self.layer_params.append(attention_w)
#                 if attention_b not in self.layer_params:
#                     self.layer_params.append(attention_b)
#                 if attention_output_w not in self.layer_params:
#                     self.layer_params.append(attention_output_w)
#                 if attention_output_b not in self.layer_params:
#                     self.layer_params.append(attention_output_b)
            self.news_field_embed_final_batch = tf.squeeze(news_field_embed)
            click_field_embed_final_batch = tf.squeeze(click_field_embed_final)

        return click_field_embed_final_batch, self.news_field_embed_final_batch

    def _kims_cnn(self, word, entity, params):
        """The KCNN module. KCNN is an extension of traditional CNN that incorporates symbolic knowledge from
        a knowledge graph into sentence representation learning.
        Args:
            word (obj): word indices for the sentence.
            entity (obj): entity indices for the sentence. Entities are aligned with words in the sentence.
            params (obj): global hyper-parameters.

        Returns:
            obj: Sentence representation.
        """
        # kims cnn parameter
        filter_sizes = params["filter_sizes"]
        num_filters = params["n_filters"]

        dim = params["word_dim"]
#         embedded_chars = tf.nn.embedding_lookup(self.word_embeddings, word)
        embedded_chars = word
        if params["use_entity"] and params["use_context"]:
            entity_embedded_chars = tf.nn.embedding_lookup(
                self.entity_embeddings, entity
            )
            context_embedded_chars = tf.nn.embedding_lookup(
                self.context_embeddings, entity
            )
            concat = tf.concat(
                [embedded_chars, entity_embedded_chars, context_embedded_chars], axis=-1
            )
            print("concat is {}".format(concat))
        elif params["use_entity"]:
#             entity_embedded_chars = tf.nn.embedding_lookup(
#                 self.entity_embeddings, entity
#             )
            entity_embedded_chars = entity
            concat = tf.concat([embedded_chars, entity_embedded_chars], axis=-1)
        else:
            concat = embedded_chars
        concat_expanded = tf.expand_dims(concat, -1)

        # Create a convolution + maxpool layer for each filter size
        pooled_outputs = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.compat.v1.variable_scope(
                "conv-maxpool-%s" % filter_size, initializer=self.initializer
            ):
                # Convolution Layer
                if params["use_entity"] and params["use_context"]:
                    filter_shape = [filter_size, dim + params["entity_dim"] * 2, 1, num_filters]
                elif params["use_entity"]:
                    filter_shape = [filter_size, dim + params["entity_dim"], 1, num_filters]
                else:
                    filter_shape = [filter_size, dim, 1, num_filters]
                W = tf.compat.v1.get_variable(
                    name="W" + "_filter_size_" + str(filter_size),
                    shape=filter_shape,
                    dtype=tf.float32,
                    initializer=tf.contrib.layers.xavier_initializer(uniform=False),
                )
                b = tf.compat.v1.get_variable(
                    name="b" + "_filter_size_" + str(filter_size),
                    shape=[num_filters],
                    dtype=tf.float32,
                )
#                 if W not in self.layer_params:
#                     self.layer_params.append(W)
#                 if b not in self.layer_params:
#                     self.layer_params.append(b)
                conv = tf.nn.conv2d(
                    concat_expanded,
                    W,
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="conv",
                )
                # Apply nonlinearity
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu")
                # Maxpooling over the outputs
                pooled = tf.nn.max_pool2d(
                    h,
                    ksize=[1, params["max_title_length"] - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="pool",
                )
                pooled_outputs.append(pooled)
        # Combine all the pooled features
        # self.num_filters_total is the kims cnn output dimension
        self.num_filters_total = num_filters * len(filter_sizes)
        h_pool = tf.concat(pooled_outputs, axis=-1)
        h_pool_flat = tf.reshape(h_pool, [-1, self.num_filters_total])
        return h_pool_flat

    def _l2_loss(self):
        l2_loss = tf.zeros([1], dtype=tf.float32)
        # embedding_layer l2 loss
        for param in self.embed_params:
            l2_loss = tf.add(
                l2_loss, tf.multiply(self.params["embed_l2"], tf.nn.l2_loss(param))
            )
        params = self.layer_params
        for param in params:
            l2_loss = tf.add(
                l2_loss, tf.multiply(self.params["layer_l2"], tf.nn.l2_loss(param))
            )
        return l2_loss

    def _l1_loss(self):
        l1_loss = tf.zeros([1], dtype=tf.float32)
        # embedding_layer l2 loss
        for param in self.embed_params:
            l1_loss = tf.add(
                l1_loss, tf.multiply(self.params["embed_l1"], tf.norm(param, ord=1))
            )
        params = self.layer_params
        for param in params:
            l1_loss = tf.add(
                l1_loss, tf.multiply(self.params["layer_l1"], tf.norm(param, ord=1))
            )
        return l1_loss

    def _cross_l_loss(self):
        """Construct L1-norm and L2-norm on cross network parameters for loss function.
        Returns:
            obj: Regular loss value on cross network parameters.
        """
        cross_l_loss = tf.zeros([1], dtype=tf.float32)
        for param in self.cross_params:
            cross_l_loss = tf.add(
                cross_l_loss, tf.multiply(self.params["cross_l1"], tf.norm(param, ord=1))
            )
            cross_l_loss = tf.add(
                cross_l_loss, tf.multiply(self.params["cross_l2"], tf.norm(param, ord=2))
            )
        return cross_l_loss

    def _build_train(self, params):
        with tf.name_scope('train'):
            self.base_loss = tf.reduce_mean(
                tf.nn.sigmoid_cross_entropy_with_logits(
                    logits=self.logit,
                    labels=self.labels
                )
            )
            self.l2_loss = tf.Variable(tf.constant(
                0., dtype=tf.float32), trainable=False)
#             for param in self.reg_params:
#                 self.l2_loss = tf.add(
#                     self.l2_loss, params["l2_weight"] * tf.nn.l2_loss(param))
            if params["transform"]:
                self.l2_loss = tf.add(
                    self.l2_loss, tf.compat.v1.losses.get_regularization_loss())
            # self.loss = self.base_loss + self.l2_loss
            # self.loss = self.base_loss
#             self.embed_regular_loss = tf.add_n(tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES))
            self.regular_loss = self._l2_loss() + self._l1_loss() + self._cross_l_loss()
            self.loss = tf.add(self.base_loss, self.regular_loss)
#             self.loss = tf.add(self.loss, self.embed_regular_loss)
            self.optimizer = tf.compat.v1.train.AdamOptimizer(
                FLAGS.learning_rate).minimize(self.loss)

def input_fn(filenames='', channel='training', batch_size=32, num_epochs=1, perform_shuffle=False):
    # print('Parsing', filenames)
    max_title_length = FLAGS.max_title_length
    if FLAGS.data_dir == '':
        raw_dir = os.environ.get('SM_CHANNEL_TRAIN')
    else:
        raw_dir = os.path.join(FLAGS.data_dir, 'train')
     
    def decode_txt(line):
        # print("test line {}".format(line))
        max_click_history = FLAGS.max_click_history
        max_title_length = FLAGS.max_title_length
        line = tf.expand_dims(line, axis=0)
        # print("test more axis line {}".format(line))
        columns = tf.string_split(line, '\t')
        # print("test collumns {}".format(columns))
        user_id = tf.strings.to_number(columns.values[0], out_type=tf.int32)
        label = tf.strings.to_number(columns.values[3], out_type=tf.float32)
        ids = []
        # click history to be added

        for i in range(1, 3):
            raw1 = tf.string_split([columns.values[i]], '[').values
            raw2 = tf.string_split(raw1, ']').values
            sparse_modify_tensor = tf.string_split(raw2, ',')
            # sparse_modify_tensor = tf.string_split([columns.values[i]], ',')
            modify_tensor = tf.reshape(
                sparse_modify_tensor.values, [max_title_length])
            # ids.append(tf.squeeze(modify_tensor))
            ids.append(modify_tensor)
            ids[i-1] = tf.strings.to_number(ids[i-1], out_type=tf.int32)

        click_ids = []

        for i in range(4, 6):
            # raw1 = tf.string_split([columns.values[i]], '[').values
            # raw2 = tf.string_split(raw1, ']').values
            # sparse_modify_tensor = tf.string_split(raw2, '-')
            sparse_modify_tensor = tf.string_split([columns.values[i]], '-')

            def judge(sparse):
                empty = tf.constant('""')
                return tf.math.equal(sparse.values[0], empty)

            def org(max_click_history, max_title_length):
                return tf.zeros([max_click_history, max_title_length], tf.int32)

            def update(sparse, max_click_history, max_title_length):
                two_d_t = []
                update_indices = []
                t_list = []
                for i in range(max_title_length):
                    t_list.append('0')
                base_t = tf.constant([t_list])

                raw1_t = tf.string_split(sparse.values, '[')
                raw2_t = tf.string_split(raw1_t.values, ']')
                string_t = tf.string_split(raw2_t.values, ',').values
                string_t = tf.reshape(string_t, [-1, max_title_length])

                for j in range(max_click_history):
                    string_t = tf.concat([string_t, base_t], 0)

                return tf.strings.to_number(tf.slice(string_t, [0, 0], [max_click_history, max_title_length], 'debug_slice_zay'), tf.int32)

            click_ids.append(tf.cond(judge(sparse_modify_tensor), lambda: org(max_click_history, max_title_length),
                                     lambda: update(sparse_modify_tensor, max_click_history, max_title_length)))

        feat = {"user_id": user_id, "news_words": ids[0], "news_entities": ids[1],
                "click_words": click_ids[0], "click_entities": click_ids[1]}
        return feat, label

    dataset = tf.data.TextLineDataset(filenames)
    # dataset = dataset.skip(1)

    if perform_shuffle:
        dataset = dataset.shuffle(buffer_size=1024*1024)

    dataset = dataset.map(
        decode_txt, num_parallel_calls=tf.data.experimental.AUTOTUNE)

    if num_epochs > 1:
        dataset = dataset.repeat(num_epochs)

    dataset = dataset.batch(
        batch_size, drop_remainder=True)  # Batch size to use

    dataset = dataset.cache()

    dataset = dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

    iterator = tf.compat.v1.data.make_one_shot_iterator(dataset)
    batch_features_index, batch_labels = iterator.get_next()
    
    word_embs = np.load(os.path.join(raw_dir,'word_embeddings_' + str(FLAGS.word_dim) + '.npy'))
    entity_embs = np.load(os.path.join(raw_dir,'entity_embeddings_' +
                                      FLAGS.KGE + '_' + str(FLAGS.entity_dim) + '.npy'))
    context_embs = np.load(os.path.join(raw_dir,'context_embeddings_' +
                                      FLAGS.KGE + '_' + str(FLAGS.entity_dim) + '.npy'))

    word_embeddings = tf.Variable(word_embs, trainable=False, dtype=np.float32, name='word')
    entity_embeddings = tf.Variable(entity_embs, trainable=False, dtype=np.float32, name='entity')
    context_embeddings = tf.Variable(context_embs, trainable=False, dtype=np.float32, name='context')
    
    batch_features = {}
    batch_features['click_words'] = tf.nn.embedding_lookup(word_embeddings, tf.reshape(batch_features_index["click_words"],[-1,max_title_length]))
    batch_features['click_entities']  = tf.nn.embedding_lookup(entity_embeddings, tf.reshape(batch_features_index["click_entities"],[-1,max_title_length]))
    batch_features['news_words'] = tf.nn.embedding_lookup(word_embeddings, batch_features_index["news_words"])
    batch_features['news_entities'] = tf.nn.embedding_lookup(entity_embeddings, batch_features_index["news_entities"])

    return batch_features, batch_labels


def model_fn(features, labels, mode, params):
    """Bulid Model function f(x) for Estimator."""
    dkn_model = DKN(params, features, labels)

    pred = dkn_model.output
    predictions = {"prob": pred}

    export_outputs = {
        tf.saved_model.DEFAULT_SERVING_SIGNATURE_DEF_KEY: tf.estimator.export.PredictOutput(predictions)}
    # Provide an estimator spec for `ModeKeys.PREDICT`
    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=predictions,
            export_outputs=export_outputs)

    # ------bulid loss------
    dkn_model._build_train(params)
    loss = dkn_model.loss
    # Provide an estimator spec for `ModeKeys.EVAL`
    # eval_logging_hook = tf.estimator.LoggingTensorHook(
    #     {'eval_labels': labels, 'eval_pred': pred, 'eval_loss':loss}, every_n_iter=1)
    # eval_metric_ops = {
    #     "auc": tf.metrics.auc(labels, pred)
    # }
    auc_metric = tf.compat.v1.metrics.auc(labels, pred)
    eval_metric_ops = {
        # "auc": roc_auc_score(y_true=labels, y_score=pred)
        "auc": auc_metric
    }

    if mode == tf.estimator.ModeKeys.EVAL:
        return tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=predictions,
            loss=loss,
            # evaluation_hooks=[eval_logging_hook],
            eval_metric_ops=eval_metric_ops)

    # optimizer = dkn_model.optimizer

    train_op = tf.train.AdamOptimizer(FLAGS.learning_rate).minimize(
        loss, global_step=tf.train.get_or_create_global_step())

    # Provide an estimator spec for `ModeKeys.TRAIN` modes
#     train_logging_hook = tf.estimator.LoggingTensorHook(
#         {'train_labels': labels, 'train_pred': pred, 'train_loss':loss}, every_n_iter=1)
    
    if mode == tf.estimator.ModeKeys.TRAIN:
        return tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=predictions,
            loss=loss,
#             training_hooks=[train_logging_hook],
            train_op=train_op)


def main(_):
    print("check input params: ")
    print(sys.argv)

    if FLAGS.dt_dir == "":
        FLAGS.dt_dir = (date.today() + timedelta(-1)).strftime('%Y%m%d')

    print('task_type ', FLAGS.task_type)
    print('model_dir ', FLAGS.model_dir)
    print('checkpoint_dir ', FLAGS.checkpointPath)
    print('data_dir ', FLAGS.data_dir)
    print('dt_dir ', FLAGS.dt_dir)
    print('num_epochs ', FLAGS.num_epochs)
    print('batch_size ', FLAGS.batch_size)
    print('loss_type ', FLAGS.loss_type)
    print('optimizer ', FLAGS.optimizer)
    print('learning_rate ', FLAGS.learning_rate)
    print('embed_l2 ', FLAGS.embed_l2)
    print('layer_l2 ', FLAGS.layer_l2)
    print('shuffle ', FLAGS.perform_shuffle)
    print('use_context ', FLAGS.use_context)

    # check train/test path
    if FLAGS.data_dir == '':
        train_data_dir = os.environ.get('SM_CHANNEL_TRAIN')
        eval_data_dir = os.environ.get('SM_CHANNEL_EVAL')
    else:
        train_data_dir = os.path.join(FLAGS.data_dir, 'train')
        eval_data_dir = os.path.join(FLAGS.data_dir, 'val')
    print("train dir is {}".format(train_data_dir))
    print("eval dir is {}".format(eval_data_dir))
    # tr_files = os.path.join(train_data_dir, 'train.csv')
    tr_files = glob.glob("%s/*.csv" % train_data_dir)
    print("tr_files:", tr_files)
    # va_files = os.path.join(eval_data_dir, 'validation.csv')
    va_files = glob.glob("%s/*.csv" % eval_data_dir)
    print("va_files:", va_files)
    te_files = None
    print("te_files:", te_files)

    if FLAGS.clear_existing_model:
        try:
            shutil.rmtree(FLAGS.model_dir)
        except Exception as e:
            print(e, "at clear_existing_model")
        else:
            print("existing model cleaned at %s" % FLAGS.model_dir)

    model_params = {
        "transform": False,
        "use_entity": FLAGS.use_entity,
        "use_context": False,
        "max_click_history": FLAGS.max_click_history,
        "n_filters": FLAGS.n_filters,
        "filter_sizes": FLAGS.filter_sizes,
        # "SEED": FLAGS.SEED,
        "KGE": FLAGS.KGE,
        "entity_dim": FLAGS.entity_dim,
        "word_dim": FLAGS.word_dim,
        "max_title_length": FLAGS.max_title_length,
        "l2_weight": FLAGS.l2_weight,
        "layer_sizes": FLAGS.layer_sizes,
        "loss_weight": FLAGS.loss_weight,
        "dropout": FLAGS.dropout,
        "activation": FLAGS.activation,
        "attention_layer_sizes": FLAGS.attention_layer_sizes,
        "attention_activation": FLAGS.attention_activation,
        "embed_l1": FLAGS.embed_l1,
        "layer_l1": FLAGS.layer_l1,
        "embed_l2": FLAGS.embed_l2,
        "layer_l2": FLAGS.layer_l2
    }

    config = tf.compat.v1.ConfigProto()
    config.gpu_options.allow_growth = True

    print("sagemaker mode building ...")
    dkn_estimator = tf.estimator.Estimator(model_fn=model_fn, model_dir=FLAGS.checkpointPath,
                                            params=model_params, config=tf.estimator.RunConfig().replace(session_config=config))
    if FLAGS.task_type == 'train':
        """
        train_spec = tf.estimator.TrainSpec(input_fn=lambda: input_fn(tr_files, channel='training', num_epochs=FLAGS.num_epochs, batch_size=FLAGS.batch_size), hooks=[bcast_hook])
        eval_spec = tf.estimator.EvalSpec(input_fn=lambda: input_fn(va_files, channel='evaluation', num_epochs=1, batch_size=FLAGS.batch_size), steps=None, start_delay_secs=1000, throttle_secs=1200)
        tf.estimator.train_and_evaluate(NCF, train_spec, eval_spec)

        """
        i = 1
        for _ in range(FLAGS.num_epochs):
            train_result = dkn_estimator.train(input_fn=lambda: input_fn(
                tr_files, num_epochs=1, batch_size=FLAGS.batch_size, perform_shuffle=FLAGS.perform_shuffle))
            print("finish train, start eval")
            eval_result = dkn_estimator.evaluate(input_fn=lambda: input_fn(
                va_files, num_epochs=1, batch_size=FLAGS.batch_size))
            print("sagemaker mode epoch %d test_auc is %.4f" %
                    (i, eval_result['auc']))
            i = i + 1
    elif FLAGS.task_type == 'eval':
        dkn_estimator.evaluate(input_fn=lambda: input_fn(
            va_files, num_epochs=1, batch_size=FLAGS.batch_size))
    elif FLAGS.task_type == 'infer':
        preds = dkn_estimator.predict(input_fn=lambda: input_fn(
            te_files, num_epochs=1, batch_size=FLAGS.batch_size), predict_keys="prob")

    if FLAGS.task_type == 'export' or FLAGS.task_type == 'train':
        feature_spec = {
            'click_words': tf.placeholder(
                dtype=tf.float32, shape=[None, model_params["max_title_length"], model_params["word_dim"]], name='click_words'),
            'click_entities': tf.placeholder(
                dtype=tf.float32, shape=[None, model_params["max_title_length"], model_params["entity_dim"]], name='click_entities'),
            'news_words': tf.placeholder(
                dtype=tf.float32, shape=[None, model_params["max_title_length"], model_params["word_dim"]], name='news_words'),
            'news_entities': tf.placeholder(
                dtype=tf.float32, shape=[None, model_params["max_title_length"], model_params["entity_dim"]], name='news_entities')
        }

        serving_input_receiver_fn_no_embed = tf.estimator.export.build_raw_serving_input_receiver_fn(
            feature_spec)

        dkn_estimator.export_savedmodel(FLAGS.servable_model_dir,
                                        serving_input_receiver_fn_no_embed)
        print("finish saving model!")

if __name__ == "__main__":
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.INFO)

    tf.compat.v1.app.run()