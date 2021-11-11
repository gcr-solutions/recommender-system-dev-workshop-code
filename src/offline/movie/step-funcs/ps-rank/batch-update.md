# Batch update

## Action processing
- input:
```
sample-data-movie/system/ingest-data/action/*.csv
sample-data-movie/system/item-data/item.csv
sample-data-movie/system/user-data/user.csv

```
- output:
```
sample-data-movie/system/action-data/action.csv
```


## Portrait batch
- input:
```
sample-data-movie/system/action-data/action.csv
sample-data-movie/feature/recommend-list/portrait/portrait.pickle
sample-data-movie/feature/content/inverted-list/movie_id_movie_property_dict.pickle
```
- output:
```
sample-data-movie/feature/recommend-list/portrait/portrait.pickle
```


## Recall batch
- input:
```
sample-data-movie/system/action-data/action.csv
sample-data-movie/feature/recommend-list/portrait/portrait.pickle
sample-data-movie/feature/content/inverted-list/movie_id_movie_property_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_type_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_entities_movie_ids_dict.pickle 
sample-data-movie/feature/content/inverted-list/movie_keywords_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_words_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/recall_config.pickle 
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



