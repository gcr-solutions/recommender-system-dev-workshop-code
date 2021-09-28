#!/usr/bin/env bash
set -e

dns_name=$(kubectl get svc istio-ingressgateway-movie-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

if [[ $REGION =~ cn.* ]];then
  dns_name=$dns_name:22
fi

if [[ -z $METHOD ]];then
  METHOD="customize"
fi

echo "endpoint: $dns_name"

#inverted-list
echo "load pickle data!!"
curl -X POST -d '{"message": {"file_type": "inverted-list", "file_path": "sample-data-movie/notification/inverted-list/","file_name": ["embed_raw_item_mapping.pickle","embed_raw_user_mapping.pickle","filter_batch_result.pickle","movie_actor_movie_ids_dict.pickle","movie_category_movie_ids_dict.pickle","movie_director_movie_ids_dict.pickle","movie_id_movie_feature_dict.pickle","movie_id_movie_property_dict.pickle","movie_language_movie_ids_dict.pickle","movie_level_movie_ids_dict.pickle","movie_year_movie_ids_dict.pickle","portrait.pickle","rank_batch_result.pickle","raw_embed_item_mapping.pickle","raw_embed_user_mapping.pickle","recall_batch_result.pickle","recall_config.pickle","filter_config.pickle"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# action-model
echo -e "\nload model data!!"
curl -X POST -d '{"message": {"file_type": "action-model","file_path": "sample-data-movie/notification/action-model/","file_name": ["deepfm_model.tar.gz", "user_embeddings.h5"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# embedding
echo -e "\nload embedding data!!"
curl -X POST -d '{"message": {"file_type": "embedding","file_path": "sample-data-movie/notification/embeddings/","file_name": ["ub_item_embeddings.npy","user_embeddings.h5"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# item record data
echo -e "\nload movie record data!!"
curl -X POST -d '{"message": {"file_type": "movie_records","file_path": "sample-data-movie/system/item-data/","file_name": ["item.csv"]}}' -H "Content-Type:application/json" http://$dns_name/api/v1/demo/notice

# item vector index data
echo -e "\nload item vector index!!"
curl -X POST -d '{"message": {"file_type": "vector-index","file_path": "sample-data-movie/notification/vector-index/","file_name": ["ub_item_vector.index"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

if [[ "${METHOD}" != "customize" ]];then
# personalize data
  echo -e "\nload personalize data!!"
  curl -X POST -d '{"message": {"file_type": "ps-result","file_path": "sample-data-movie/system/ps-config/","file_name": ["ps_config.json"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice
fi

if [[ "${METHOD}" = "ps-sims" || "${METHOD}" = "all" ]];then
  # ps-sims data
  echo -e "\nload personalize sims item data!!"
  curl -X POST -d '{"message": {"file_type": "ps-sims-dict","file_path": "sample-data-movie/notification/ps-sims-dict/","file_name": ["ps-sims-batch.out"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice
fi

echo -e '\nLoad seed data complete!'


if [[  -z $NOT_PRINTING_CONTROL_C ]];then
   echo "Please stop printing the log by typing CONTROL+C "
fi
