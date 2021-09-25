
## Prepare action data

- input:

```
sample-data-news/system/ingest-data/action/*.csv
```

- output:

```
sample-data-news/system/popularity-action-data/action.csv
```

## Inverted list

- input:

```
sample-data-news/system/popularity-action-data/action.csv (optional)
sample-data-news/feature/content/inverted-list/news_id_news_feature_dict.pickle(optional)

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
