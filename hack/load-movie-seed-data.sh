dns_name=$1

echo service_endpoint: $dns_name

#inverted-list
echo "load pickle data!!"
curl -X POST -d '{"message": {"file_type": "inverted-list", "file_path": "sample-data-movie/notification/inverted-list/","file_name": ["embed_raw_item_mapping.pickle","embed_raw_user_mapping.pickle","filter_batch_result.pickle","filter_config.pickle","movie_actor_movie_ids_dict.pickle","movie_category_movie_ids_dict.pickle","movie_director_movie_ids_dict.pickle","movie_id_movie_feature_dict.pickle","movie_id_movie_property_dict.pickle","movie_language_movie_ids_dict.pickle","movie_level_movie_ids_dict.pickle","movie_year_movie_ids_dict.pickle","portrait.pickle","rank_batch_result.pickle","raw_embed_item_mapping.pickle","raw_embed_user_mapping.pickle","recall_batch_result.pickle","recall_config.pickle"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# action-model
echo -e "\nload model data!!"
curl -X POST -d '{"message": {"file_type": "action-model","file_path": "sample-data-movie/notification/action-model/","file_name": ["deepfm_model.tar.gz", "user_embeddings.h5"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# vector data
echo "\nload model data!!"
curl -X POST -d '{"message": {"file_type": "vector-index","file_path": "sample-data-movie/notification/vector-index/","file_name": ["ub_item_vector.index"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# embedding
echo -e "\nload embedding data!!"
curl -X POST -d '{"message": {"file_type": "embedding","file_path": "sample-data-movie/notification/embeddings/","file_name": ["ub_item_embeddings.npy"]}}' -H "Content-Type:application/json" http://$dns_name/loader/notice

# item record data
echo -e "\nload movie record data!!"
curl -X POST -d '{"message": {"file_type": "movie_records","file_path": "sample-data-movie/system/item-data/","file_name": ["item.csv"]}}' -H "Content-Type:application/json" http://$dns_name/api/v1/demo/notice

echo -e '\nLoad seed data complete!'