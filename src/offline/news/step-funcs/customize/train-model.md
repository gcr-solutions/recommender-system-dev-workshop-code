# Train Model

## Prepare training data
- input:
```
sample-data-news/system/ingest-data/action/action.csv

sample-data-news/feature/content/inverted-list/news_id_news_feature_dict.pickle
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






