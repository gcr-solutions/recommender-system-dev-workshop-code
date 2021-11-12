# Item New

## Item data processing

- input:

```
sample-data-news/system/ingest-data/item/*.csv
```

- output:

```
sample-data-news/system/item-data/item.csv
```

## Add item batch

- input:

```
sample-data-news/system/user-data/item.csv
```

- output:

```
sample-data-news/feature/action/raw_embed_item_mapping.pickle
sample-data-news/feature/action/embed_raw_item_mapping.pickle
```

## Item feature update batch

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

## Model update (embeding)

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



