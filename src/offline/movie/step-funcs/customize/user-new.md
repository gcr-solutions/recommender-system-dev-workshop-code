# User New

## User processing
- input 
``` 
sample-data-movie/system/ingest-data/user/*.csv

```

- output
``` 
sample-data-movie/system/user-data/user.csv
```
## Add user batch

- input 
``` 
sample-data-movie/system/user-data/user.csv
```

- output
``` 
sample-data-movie/feature/action/raw_embed_user_mapping.pickle
sample-data-movie/feature/action/embed_raw_user_mapping.pickle
```