#!/usr/bin/env bash
set -e

#create dataset group
#datasetGroupArn=$(aws personalize create-dataset-group --name GCR-RS-News-Dataset-Group --output text)
#echo "dataset_Group_Arn: ${datasetGroupArn}"
datasetGroupArn="arn:aws:personalize:ap-northeast-1:466154167985:dataset-group/GCR-RS-News-Dataset-Group"


# #delete exist schema
# echo "deleting Schema..."
# aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsUserSchema"
# aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsItemSchema"
# aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsInteractionSchema"

# sleep 10

# #create schema
# echo "creating Schema..."
# user_schema_arn=$(aws personalize create-schema \
# 	--name NewsUserSchema \
# 	--schema file://./personalize/NewsUserSchema.json --output text)

# item_schema_arn=$(aws personalize create-schema \
# 	--name NewsItemSchema \
# 	--schema file://./personalize/NewsItemSchema.json --output text)

# interaction_schema_arn=$(aws personalize create-schema \
# 	--name NewsInteractionSchema \
# 	--schema file://./personalize/NewsInteractionSchema.json --output text)

# #delete dataset

# #create dataset
# echo "create dataset..."
# user_dataset_arn=$(aws personalize create-dataset \
# 	--name NewsUserDataset \
# 	--dataset-group-arn ${datasetGroupArn} \
# 	--dataset-type Users \
# 	--schema-arn ${user_schema_arn} --output text)

# item_dataset_arn=$(aws personalize create-dataset \
# 	--name NewsItemDataset \
# 	--dataset-group-arn ${datasetGroupArn} \
# 	--dataset-type Items \
# 	--schema-arn ${item_schema_arn} --output text)
	
# interaction_dataset_arn=$(aws personalize create-dataset \
# 	--name NewsInteractionDataset \
# 	--dataset-group-arn ${datasetGroupArn} \
# 	--dataset-type Interactions \
# 	--schema-arn ${interaction_schema_arn} --output text)

#for test
user_dataset_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset/GCR-RS-News-Dataset-Group/USERS"
item_dataset_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset/GCR-RS-News-Dataset-Group/ITEMS"
interaction_dataset_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset/GCR-RS-News-Dataset-Group/INTERACTIONS"



#Get Bucket Name
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity  --o text | awk '{print $1}')
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET_BUILD=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}

echo "BUCKET_BUILD=${BUCKET_BUILD}"
echo "Create S3 Bucket: ${BUCKET_BUILD} if not exist"

PERSONALIZE_ROLE_BUILD=arn:aws:iam::${AWS_ACCOUNT_ID}:role/gcr-rs-${Stage}-personalize-role
echo "PERSONALIZE_ROLE_BUILD=${PERSONALIZE_ROLE_BUILD}"
echo "Check if your personalize role arn is equal to the PERSONALIZE_ROLE_BUILD. If not, please follow the previous step to create iam role for personalize!"

# echo "\nWaiting for creating dataset finishing...\n"
# sleep 60

# #create import job
# user_dataset_import_job_arn=$(aws personalize create-dataset-import-job \
#   --job-name NewsUserImportJob \
#   --dataset-arn ${user_dataset_arn} \
#   --data-source dataLocation=s3://${BUCKET_BUILD}/sample-data-news/system/personalize-data/personalize_user.csv \
#   --role-arn ${PERSONALIZE_ROLE_BUILD} \
#   --output text)
  
  
# item_dataset_import_job_arn=$(aws personalize create-dataset-import-job \
#   --job-name NewsItemImportJob \
#   --dataset-arn ${item_dataset_arn} \
#   --data-source dataLocation=s3://${BUCKET_BUILD}/sample-data-news/system/personalize-data/personalize_item.csv \
#   --role-arn ${PERSONALIZE_ROLE_BUILD} \
#   --output text)
  
interaction_dataset_import_job_arn=$(aws personalize create-dataset-import-job \
  --job-name NewsInteractionImportJob \
  --dataset-arn ${interaction_dataset_arn} \
  --data-source dataLocation=s3://${BUCKET_BUILD}/sample-data-news/system/personalize-data/personalize_interactions.csv \
  --role-arn ${PERSONALIZE_ROLE_BUILD} \
  --output text)
 
  
#for test
user_dataset_import_job_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset-import-job/NewsUserImportJob"
item_dataset_import_job_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset-import-job/NewsItemImportJob"

#monitor import job
echo "Data Importing... It will takes no longer than 10 min..."
MAX_TIME=10*60 # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    user_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
                --dataset-import-job-arn ${user_dataset_import_job_arn} | jq '.datasetImportJob.status')
    item_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
                --dataset-import-job-arn ${item_dataset_import_job_arn} | jq '.datasetImportJob.status')
    interaction_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
                --dataset-import-job-arn ${interaction_dataset_import_job_arn} | jq '.datasetImportJob.status')

    echo "user_dataset_import_job_status: ${user_dataset_import_job_status}"
    echo "item_dataset_import_job_status: ${item_dataset_import_job_status}"
    echo "interaction_dataset_import_job_status: ${interaction_dataset_import_job_status}"
    
    if [[ $user_dataset_import_job_status = "CREATE FAILED" || $item_dataset_import_job_status = "CREATE FAILED" || $interaction_dataset_import_job_status = "CREATE FAILED" ]]
    then
        echo "!!!Dataset Import Job Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ $user_dataset_import_job_status = "ACTIVE" && $item_dataset_import_job_status = "ACTIVE" && $interaction_dataset_import_job_status = "ACTIVE" ]]
    then
        echo "Import Job finishing successfully!"
        break
    fi
    
    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Import Job Time exceed 10 min, please delete import job and try again!"
    exit 8
fi


#create solution
userPersonalize_solution_arn=$(aws personalize create-solution \
        --name gcr-rs-dev-workshop-news-solution \
        --dataset-group-arn ${datasetGroupArn} \
        --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization
        --output text)


#monitor solution
echo "Solution Creating... It will takes no longer than 10 min..."
MAX_TIME=10*60 # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    userPersonalize_solution_status=$(aws personalize describe-solution \
        --solution-arn ${userPersonalize_solution_arn} | jq '.solution.status')
    
    echo "userPersonalize_solution_status: ${userPersonalize_solution_status}"
    
    if [[ $userPersonalize_solution_status = "CREATE FAILED" ]]
    then
        echo "!!!UserPersonalize Solution Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ $userPersonalize_solution_status = "ACTIVE" ]]
    then
        echo "UserPersonalize Solution  create successfully!"
        break
    fi

    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating UserPersonalize Solution Time exceed 10 min, please delete UserPersonalize Solution and try again!"
    exit 8
fi



#create solution version
userPersonalize_solution_version_arn=$(aws personalize create-solution-version \
        --solution-arn ${userPersonalize_solution_arn} 
        --output text)


#monitor solution version
echo "Solution Version Creating... It will takes no longer than 6 hours..."
MAX_TIME=6*60*60 # 6 hours
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    userPersonalize_solution_version_status=$(aws personalize describe-solution-version \
            --solution-version-arn ${userPersonalize_solution_version_arn} | jq '.solutionVersion.status')
            
    echo "userPersonalize_solution_version_status: ${userPersonalize_solution_version_status}"
    
    if [[ $userPersonalize_solution_version_status = "CREATE FAILED" ]]
    then
        echo "!!!UserPersonalize Solution Version Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ $userPersonalize_solution_version_status = "ACTIVE" ]]
    then
        echo "UserPersonalize Solution Version create successfully!"
        break
    fi

    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating UserPersonalize Solution Version Time exceed 10 min, please delete UserPersonalize Solution Version and try again!"
    exit 8
fi


#print metrics
echo "UserPersonalize Solution Metrics:"
aws personalize get-solution-metrics --solution-version-arn ${userPersonalize_solution_version_arn}


#create campaign
userPersonalize_campaign_arn=$(aws personalize create-campaign \
        --name gcr-rs-dev-workshop-news-userPersonalize-campaign \
        --solution-version-arn ${userPersonalize_solution_version_arn} \
        --min-provisioned-tps 1
        --output text)


#monitor campaign
echo "Campaign Creating... It will takes no longer than 3 hours..."
MAX_TIME=3*60*60 # 6 hours
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    userPersonalize_campaign_status=$(aws personalize describe-campaign \
            --campaign-arn ${userPersonalize_campaign_arn} | jq '.campaign.status')
            
    echo "userPersonalize_campaign_status: ${userPersonalize_campaign_status}"
    
    if [[ $userPersonalize_campaign_status = "CREATE FAILED" ]]
    then
        echo "!!!UserPersonalize Campaign Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ $userPersonalize_campaign_status = "ACTIVE" ]]
    then
        echo "UserPersonalize Campaign create successfully!"
        break
    fi

    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating UserPersonalize Campaign Time exceed 10 min, please delete UserPersonalize Campaign and try again!"
    exit 8
fi


echo "Congratulations!!! Your AWS Personalize Service Create Successfully!!!"







    
    
    


	



