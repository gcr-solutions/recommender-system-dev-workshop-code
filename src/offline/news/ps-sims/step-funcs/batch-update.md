# Batch update

## Action processing
- input:
```
sample-data-news/system/ingest-data/action/*.csv
sample-data-news/system/item-data/item.csv
sample-data-news/system/user-data/user.csv

```
- output:
```
sample-data-news/system/action-data/action.csv
```


## Portrait batch
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


## Recall batch
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


## Rank batch
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


## Filter batch
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



