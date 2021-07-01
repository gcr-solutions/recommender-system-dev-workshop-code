#!/usr/bin/env bash
set -e

#create dataset group
#datasetGroupArn=$(aws personalize create-dataset-group --name GCR-RS-News-Dataset-Group --output text)
#echo "dataset_Group_Arn: ${datasetGroupArn}"
datasetGroupArn="arn:aws:personalize:ap-northeast-1:466154167985:dataset-group/GCR-RS-News-Dataset-Group"


#delete exist schema
aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsUserSchema"
aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsItemSchema"
aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsInteractionSchema"


#create schema
user_schema_arn=$(aws personalize create-schema \
	--name NewsUserSchema \
	--schema file://./personalize/NewsUserSchema.json --output text)

item_schema_arn=$(aws personalize create-schema \
	--name NewsItemSchema \
	--schema file://./personalize/NewsItemSchema.json --output text)

interaction_schema_arn=$(aws personalize create-schema \
	--name NewsInteractionSchema \
	--schema file://./personalize/NewsInteractionSchema.json --output text)

#create dataset
user_dataset_arn=$(aws personalize create-dataset \
	--name NewsUserDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Users \
	--schema-arn ${user_schema_arn} --output text)

item_dataset_arn=$(aws personalize create-dataset \
	--name NewsItemDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Items \
	--schema-arn ${item_schema_arn} --output text)
	
item_dataset_arn=$(aws personalize create-dataset \
	--name NewsUserDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Interactions \
	--schema-arn ${interaction_schema_arn} --output text)
	



