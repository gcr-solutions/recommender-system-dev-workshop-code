#!/usr/bin/env bash
set -e

dns_name=$(kubectl get svc istio-ingressgateway-news-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

if [[ $REGION =~ cn.* ]];then
  dns_name=$dns_name:22
fi

echo "endpoint: $dns_name"

#inverted-list
echo "load pickle data!!"
curl -X POST -d '{"message": {"file_type": "inverted-list", "file_path": "sample-data-news/notification/inverted-list/","file_name": ["embed_raw_item_mapping.pickle","embed_raw_user_mapping.pickle","filter_batch_result.pickle","news_entities_news_ids_dict.pickle","news_id_news_feature_dict.pickle","news_id_news_property_dict.pickle","news_keywords_news_ids_dict.pickle","news_type_news_ids_dict.pickle","news_words_news_ids_dict.pickle","portrait.pickle","rank_batch_result.pickle","raw_embed_item_mapping.pickle","raw_embed_user_mapping.pickle","recall_batch_result.pickle","recall_config.json","filter_config.json"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# action-model
echo -e "\nload model data!!"
curl -X POST -d '{"message": {"file_type": "action-model","file_path": "sample-data-news/notification/action-model/","file_name": ["model.tar.gz"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# embedding
echo -e "\nload embedding data!!"
curl -X POST -d '{"message": {"file_type": "embedding","file_path": "sample-data-news/notification/embeddings/","file_name": ["dkn_context_embedding.npy","dkn_entity_embedding.npy","dkn_relation_embedding.npy","dkn_word_embedding.npy"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# item record data
echo -e "\nload news record data!!"
curl -X POST -d '{"message": {"file_type": "news_records","file_path": "sample-data-news/system/item-data/","file_name": ["item.csv"]}}' -H "Content-Type:application/json" http://$dns_name/api/v1/demo/notice

# personalize data
echo -e "\nload personalize data!!"
curl -X POST -d '{"message": {"file_type": "ps-result","file_path": "sample-data-news/system/ps-config/","file_name": ["ps_config.json"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# ps-sims data
echo -e "\nload personalize sims item data!!"
curl -X POST -d '{"message": {"file_type": "ps-sims-dict","file_path": "sample-data-news/notification/ps-sims-dict/","file_name": ["ps-sims-batch.out"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

echo -e '\nLoad seed data complete!'

echo "Please stop printing the log by typing CONTROL+C "
