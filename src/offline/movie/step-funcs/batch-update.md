# Batch update 

## Action processing
- input 
``` 
sample-data-movie/system/ingest-data/action/*.csv

```

- output
``` 
sample-data-movie/system/action-data/action.csv
```


## Portrait batch

- input 
``` 
sample-data-movie/system/action-data/action.csv
sample-data-movie/model/recall/youtubednn/user_embeddings.h5
sample-data-movie/feature/action/raw_embed_user_mapping.pickle
sample-data-movie/feature/action/raw_embed_item_mapping.pickle
sample-data-movie/feature/recommend-list/portrait/portrait.pickle
sample-data-movie/feature/content/inverted-list/movie_id_movie_property_dict.pickle
```

- output
``` 
sample-data-movie/feature/recommend-list/portrait/portrait.pickle

```


## Recall batch

- input 
``` 
sample-data-movie/system/action-data/action.csv
sample-data-movie/feature/action/ub_item_vector.index
sample-data-movie/feature/action/embed_raw_item_mapping.pickle
sample-data-movie/feature/recommend-list/portrait/portrait.pickle
sample-data-movie/feature/content/inverted-list/movie_id_movie_property_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_category_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_director_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_actor_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_language_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_level_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_year_movie_ids_dict.pickle 
sample-data-movie/model/recall/recall_config.pickle
```

- output
``` 
sample-data-movie/feature/recommend-list/movie/recall_batch_result.pickle
```

## Rank batch

- input 
``` 
sample-data-movie/feature/recommend-list/movie/recall_batch_result.pickle 
sample-data-movie/feature/recommend-list/portrait/portrait.pickle
sample-data-movie/feature/content/inverted-list/movie_id_movie_feature_dict.pickle 
sample-data-movie/model/rank/action/deepfm/latest/deepfm_model.tar.gz
```

- output
``` 
sample-data-movie/feature/recommend-list/movie/rank_batch_result.pickle
```

## Filter batch

- input 
``` 
sample-data-movie/feature/recommend-list/movie/recall_batch_result.pickle 
sample-data-movie/feature/recommend-list/movie/rank_batch_result.pickle
sample-data-movie/feature/content/inverted-list/movie_id_movie_property_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_category_movie_ids_dict.pickle
sample-data-movie/model/filter/filter_config.pickle
```

- output
``` 
sample-data-movie/feature/recommend-list/movie/filter_batch_result.pickle
```

