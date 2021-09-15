
# News

# Item new

### Item data processing

- input:
```
sample-data-news/system/ingest-data/item/*.csv
```

- output:
```
sample-data-news/system/item-data/item.csv
```


### User processing

- input:
```
sample-data-news/system/ingest-data/user/*.csv
```

- output:
```
sample-data-news/system/item-data/user.csv
```

### Add item user batch

- input:
```
sample-data-news/system/user-data/user.csv
sample-data-news/system/item-data/item.csv
```

- output:
```
sample-data-news/feature/action/raw_embed_user_mapping.pickle
sample-data-news/feature/action/embed_raw_user_mapping.pickle
sample-data-news/feature/action/raw_embed_item_mapping.pickle
sample-data-news/feature/action/embed_raw_item_mapping.pickle
```


### Item feature update batch

- input:
```
sample-data-news/model/rank/content/dkn_embedding_latest/complete_dkn_word_embedding.npy
sample-data-news/system/item-data/item.csv
sample-data-news/model/meta_files/vocab.json
sample-data-news/model/meta_files/entities_dbpedia.dict
sample-data-news/model/meta_files/relations_dbpedia.dict 
sample-data-news/model/meta_files/kg_dbpedia.txt

sample-data-news/model/meta_files/entities_dbpedia_train.dict
sample-data-news/model/meta_files/relations_dbpedia_train.dict
sample-data-news/model/meta_files/kg_dbpedia_train.txt
```

- output:
```
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_word_embedding.npy
sample-data-news/model/meta_files/kg_dbpedia_train.txt
sample-data-news/model/meta_files/entities_dbpedia_train.dict
sample-data-news/model/meta_files/relations_dbpedia_train.dict
sample-data-news/feature/content/inverted-list/news_id_news_feature_dict.pickle
```

### Inverted list

- input:
```
sample-data-news/system/action-data/action.csv (optional)
sample-data-news/system/item-data/item.csv

sample-data-news/model/meta_files/kg_dbpedia_train.txt
sample-data-news/model/meta_files/kg_dbpedia.txt
sample-data-news/model/meta_files/entities_dbpedia.dict
sample-data-news/model/meta_files/entities_dbpedia_train.dict
sample-data-news/model/meta_files/relations_dbpedia.dict
sample-data-news/model/meta_files/relations_dbpedia_train.dict
sample-data-news/model/meta_files/entity_industry.txt

```


- output:
```
sample-data-news/feature/content/inverted-list/news_id_news_property_dict.pickle
sample-data-news/feature/content/inverted-list/news_type_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_keywords_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_entities_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_words_news_ids_dict.pickle
```

### Model update (embeding)

- input:
```
sample-data-news/model/meta_files/kg_dbpedia_train.txt
sample-data-news/model/meta_files/kg_dbpedia.txt
sample-data-news/model/meta_files/entities_dbpedia.dict
sample-data-news/model/meta_files/entities_dbpedia_train.dict
sample-data-news/model/meta_files/relations_dbpedia.dict
sample-data-news/model/meta_files/relations_dbpedia_train.dict
sample-data-news/model/meta_files/entity_industry.txt
sample-data-news/model/meta_files/vocab.json

```


- output:
```
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_entity_embedding.npy
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_context_embedding.npy
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_relation_embedding.npy

```

### Model update (action)

- input:
```
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_entity_embedding.npy
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_context_embedding.npy
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_word_embedding.npy
sample-data-news/system/action-data/action_train.csv 
sample-data-news/system/action-data/action_val.csv 

```


- output:
```
sample-data-news/model/rank/action/dkn/latest/model.tar.gz

```

## Action new

### User processing

### Add item user batch

### Action processing
- input:
```

sample-data-news/system/ingest-data/action/*.csv

sample-data-news/feature/content/inverted-list/news_id_news_feature_dict.pickle
sample-data-news/feature/action/raw_embed_user_mapping.pickle
```

- output:
```
sample-data-news/system/action-data/action.csv
sample-data-news/system/action-data/action_train.csv
sample-data-news/system/action-data/action_val.csv
```

### Inverted list

### Portrait batch
- input:
```
sample-data-news/system/action-data/action.csv
sample-data-news/feature/recommend-list/portrait/portrait.pickle
sample-data-news/feature/content/inverted-list/news_id_news_property_dict.pickle
```

- output:
```
sample-data-news/feature/recommend-list/portrait/portrait.pickle
```


### Recall batch
- input:
```
sample-data-news/system/action-data/action.csv
sample-data-news/feature/recommend-list/portrait/portrait.pickle
sample-data-news/feature/content/inverted-list/news_id_news_property_dict.pickle
sample-data-news/feature/content/inverted-list/news_type_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_entities_news_ids_dict.pickle 
sample-data-news/feature/content/inverted-list/news_keywords_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_words_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/recall_config.pickle 
```

- output:
```
sample-data-news/feature/recommend-list/news/recall_batch_result.pickle
```


### Rank batch
- input:
```
sample-data-news/feature/recommend-list/news/recall_batch_result.pickle
sample-data-news/feature/recommend-list/portrait/portrait.pickle
sample-data-news/feature/content/inverted-list/news_id_news_property_dict.pickle
sample-data-news/feature/content/inverted-list/news_id_news_feature_dict.pickle 
sample-data-news/model/rank/action/dkn/latest/model.tar.gz 
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_entity_embedding.npy
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_context_embedding.npy
sample-data-news/model/rank/content/dkn_embedding_latest/dkn_word_embedding.npy

```

- output:
```
sample-data-news/feature/recommend-list/news/rank_batch_result.pickle

```

### Filter batch
- input:
```
sample-data-news/feature/recommend-list/news/recall_batch_result.pickle
sample-data-news/feature/recommend-list/news/rank_batch_result.pickle
sample-data-news/feature/content/inverted-list/news_id_news_property_dict.pickle
sample-data-news/feature/content/inverted-list/news_type_news_ids_dict.pickle 
sample-data-news/feature/content/inverted-list/filter_config.pickle 
```

- output:
```
sample-data-news/feature/recommend-list/news/filter_batch_result.pickle

```

### Weight update batch

- input:
```
sample-data-news/system/action-data/action.csv
sample-data-news/system/item-data/item.csv
sample-data-news/model/meta_files/kg_dbpedia_train.txt
sample-data-news/model/meta_files/kg_dbpedia.txt
sample-data-news/model/meta_files/entities_dbpedia.dict
sample-data-news/model/meta_files/entities_dbpedia_train.dict
sample-data-news/model/meta_files/relations_dbpedia.dict
sample-data-news/model/meta_files/relations_dbpedia_train.dict
sample-data-news/model/meta_files/entity_industry.txt
```

- output:
```
sample-data-news/feature/content/inverted-list/news_id_news_property_dict.pickle
sample-data-news/feature/content/inverted-list/news_type_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_keywords_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_entities_news_ids_dict.pickle
sample-data-news/feature/content/inverted-list/news_words_news_ids_dict.pickle
```

## Train model

### User processing

### Add item user batch

### Action processing

### Model update (embeding)

### Model update (action)



