# Train Model


## Generate item feature

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
sample-data-news/feature/content/inverted-list/news_id_news_feature_dict_for_train.pickle
```

## Prepare training data
- input:
```
sample-data-news/system/ingest-data/action/action.csv

sample-data-news/feature/content/inverted-list/news_id_news_feature_dict_for_train.pickle
sample-data-news/feature/action/raw_embed_user_mapping.pickle
```
- output:
```
sample-data-news/system/action-data/action_train.csv
sample-data-news/system/action-data/action_val.csv
```

## Model update (action)
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






