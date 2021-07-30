# Train model

## Prepare training data

- input
```
sample-data-movie/system/ingest-data/action/*.csv
```

- output
``` 
sample-data-movie/system/action-data/train_action.csv
```
## Model update deepfm
- input
```
sample-data-movie/system/action-data/train_action.csv 
sample-data-movie/feature/action/raw_embed_item_mapping.pickle
sample-data-movie/feature/action/raw_embed_user_mapping.pickle
sample-data-movie/model/recall/youtubednn/user_embeddings.h5 
sample-data-movie/feature/content/inverted-list/movie_id_movie_feature_dict.pickle
```

- output
``` 
sample-data-movie/model/rank/action/deepfm/latest/deepfm_model.tar.gz
```
