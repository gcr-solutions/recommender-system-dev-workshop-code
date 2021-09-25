# Item New

## Item data processing
- input 
``` 
sample-data-movie/system/ingest-data/item/*.csv

```

- output
``` 
sample-data-movie/system/item-data/item.csv
```


## Add item batch
- input 
``` 
sample-data-movie/system/item-data/item.csv
```

- output
``` 
sample-data-movie/feature/action/raw_embed_item_mapping.pickle
sample-data-movie/feature/action/embed_raw_item_mapping.pickle
```


## Item feature update batch
- input 
``` 
sample-data-movie/feature/action/raw_embed_item_mapping.pickle
sample-data-movie/feature/action/raw_embed_user_mapping.pickle 
sample-data-movie/feature/action/ub_item_embeddings.npy (optional)
sample-data-movie/feature/content/inverted-list/movie_id_movie_property_dict.pickle
sample-data-movie/system/item-data/item.csv
```

- output
``` 
sample-data-movie/feature/content/inverted-list/movie_id_movie_feature_dict.pickle
```


## Inverted list
- input 
```
sample-data-movie/system/item-data/item.csv, 

```

- output
``` 
sample-data-movie/feature/content/inverted-list/movie_id_movie_property_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_director_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_language_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_level_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_year_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_category_movie_ids_dict.pickle
sample-data-movie/feature/content/inverted-list/movie_actor_movie_ids_dict.pickle

```


## Model update ub
- input 
``` 
 sample-data-movie/system/action-data/action.csv
 sample-data-movie/feature/action/raw_embed_item_mapping.pickle 
 sample-data-movie/feature/action/raw_embed_user_mapping.pickle
```

- output
``` 
sample-data-movie/model/recall/youtubednn/user_embeddings.h5
sample-data-movie/feature/action/ub_item_vector.index
sample-data-movie/feature/action/ub_item_embeddings.npy
```



