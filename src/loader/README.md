# loader 

loader is an initiator and loading transformed data into Redis, or update data in Redis incrementally.
- name: PICKLE_PATH

    value: recommender-system-film-mk/1/notification/inverted-list/movie_actor_movie_ids_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/movie_category_movie_ids_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/movie_director_movie_ids_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/movie_id_movie_property_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/movie_id_movie_feature_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/movie_language_movie_ids_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/movie_level_movie_ids_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/movie_year_movie_ids_dict.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/embed_raw_item_mapping.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/embed_raw_user_mapping.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/raw_embed_item_mapping.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/raw_embed_user_mapping.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/portrait.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/recall_config.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/filter_config.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/recall_batch_result.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/rank_batch_result.pickle
    value: recommender-system-film-mk/1/notification/inverted-list/filter_batch_result.pickle

- name: RECORDS_PATH
   
    value: news-open/system/item-data/meta-data/

- name: VECTOR_INDEX_PATH
  
    value: recommender-system-film-mk/1/notification/vector-index/ub_item_vector.index

- name: ACTION_MODEL_PATH
    
    value: recommender-system-film-mk/1/notification/action-model/deepfm_model.tar.gz
    value: recommender-system-film-mk/1/notification/action-model/user_embeddings.h5

- name: EMBEDDING_NPY_PATH
   
    value: recommender-system-film-mk/1/notification/embeddings/ub_item_embeddings.npy
