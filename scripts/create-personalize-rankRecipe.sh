#!/usr/bin/env bash
set -e

#create dataset group
datasetGroupArn=$(aws personalize create-dataset-group --name GCR-RS-News-Ranking-Dataset-Group --output text)
echo "dataset_Group_Arn: ${datasetGroupArn}"
echo "......"
# for test
#datasetGroupArn="arn:aws:personalize:ap-northeast-1:466154167985:dataset-group/GCR-RS-News-Dataset-Group"


# #delete exist schema
# echo "deleting existing personalize Schema..."
# aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsUserSchema"
# aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsItemSchema"
# aws personalize delete-schema --schema-arn "arn:aws:personalize:ap-northeast-1:466154167985:schema/NewsInteractionSchema"

sleep 10

#create schema
echo "creating personalize ranking Schema..."
user_schema_arn=$(aws personalize create-schema \
	--name NewsRankingUserSchema \
	--schema file://./personalize/NewsUserSchema.json --output text)

item_schema_arn=$(aws personalize create-schema \
	--name NewsRankingItemSchema \
	--schema file://./personalize/NewsItemSchema.json --output text)

interaction_schema_arn=$(aws personalize create-schema \
	--name NewsRankingInteractionSchema \
	--schema file://./personalize/NewsInteractionSchema.json --output text)

echo "......"
sleep 10

#create dataset
echo "create dataset..."
user_dataset_arn=$(aws personalize create-dataset \
	--name NewsRankingUserDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Users \
	--schema-arn ${user_schema_arn} --output text)

item_dataset_arn=$(aws personalize create-dataset \
	--name NewsRankingItemDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Items \
	--schema-arn ${item_schema_arn} --output text)
	
interaction_dataset_arn=$(aws personalize create-dataset \
	--name NewsRankingInteractionDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Interactions \
	--schema-arn ${interaction_schema_arn} --output text)

# #for test
# user_dataset_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset/GCR-RS-News-Dataset-Group/USERS"
# item_dataset_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset/GCR-RS-News-Dataset-Group/ITEMS"
# interaction_dataset_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset/GCR-RS-News-Dataset-Group/INTERACTIONS"

echo "......"

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

echo "\nWaiting for creating dataset finishing...\n"
sleep 60

#create import job
echo "create dataset import job..."
user_dataset_import_job_arn=$(aws personalize create-dataset-import-job \
  --job-name NewsRankingUserImportJob \
  --dataset-arn ${user_dataset_arn} \
  --data-source dataLocation=s3://${BUCKET_BUILD}/sample-data-news/system/personalize-data/personalize_user.csv \
  --role-arn ${PERSONALIZE_ROLE_BUILD} \
  --output text)
  
  
item_dataset_import_job_arn=$(aws personalize create-dataset-import-job \
  --job-name NewsRankingItemImportJob \
  --dataset-arn ${item_dataset_arn} \
  --data-source dataLocation=s3://${BUCKET_BUILD}/sample-data-news/system/personalize-data/personalize_item.csv \
  --role-arn ${PERSONALIZE_ROLE_BUILD} \
  --output text)
  
interaction_dataset_import_job_arn=$(aws personalize create-dataset-import-job \
  --job-name NewsRankingInteractionImportJob \
  --dataset-arn ${interaction_dataset_arn} \
  --data-source dataLocation=s3://${BUCKET_BUILD}/sample-data-news/system/personalize-data/personalize_interactions.csv \
  --role-arn ${PERSONALIZE_ROLE_BUILD} \
  --output text)
 
 
echo "......"
# #for test
# user_dataset_import_job_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset-import-job/NewsUserImportJob"
# item_dataset_import_job_arn="arn:aws:personalize:ap-northeast-1:466154167985:dataset-import-job/NewsItemImportJob"

#monitor import job
echo "Data Importing... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    user_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
                --dataset-import-job-arn ${user_dataset_import_job_arn} | jq '.datasetImportJob.status' -r)
    item_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
                --dataset-import-job-arn ${item_dataset_import_job_arn} | jq '.datasetImportJob.status' -r)
    interaction_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
                --dataset-import-job-arn ${interaction_dataset_import_job_arn} | jq '.datasetImportJob.status' -r)

    echo "user_dataset_import_job_status: ${user_dataset_import_job_status}"
    echo "item_dataset_import_job_status: ${item_dataset_import_job_status}"
    echo "interaction_dataset_import_job_status: ${interaction_dataset_import_job_status}"
    
    if [[ "$user_dataset_import_job_status" = "CREATE FAILED" || "$item_dataset_import_job_status" = "CREATE FAILED" || "$interaction_dataset_import_job_status" = "CREATE FAILED" ]]
    then
        echo "!!!Dataset Import Job Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ "$user_dataset_import_job_status" = "ACTIVE" && "$item_dataset_import_job_status" = "ACTIVE" && "$interaction_dataset_import_job_status" = "ACTIVE" ]]
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
ranking_solution_arn=$(aws personalize create-solution \
        --name rankingSolution \
        --dataset-group-arn ${datasetGroupArn} \
        --recipe-arn arn:aws:personalize:::recipe/aws-personalized-ranking --output text)


#monitor solution
echo "Solution Creating... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    ranking_solution_status=$(aws personalize describe-solution \
        --solution-arn ${ranking_solution_arn} | jq '.solution.status' -r)
    
    echo "ranking_solution_status: ${ranking_solution_status}"
    
    if [ "$ranking_solution_status" = "CREATE FAILED" ]
    then
        echo "!!!Ranking Solution Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [ "$ranking_solution_status" = "ACTIVE" ]
    then
        echo "Ranking Solution create successfully!"
        break;
    fi
    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Ranking Solution Time exceed 10 min, please delete Ranking Solution and try again!"
    exit 8
fi



#create solution version
ranking_solution_version_arn=$(aws personalize create-solution-version \
        --solution-arn ${ranking_solution_arn} --output text)


#monitor solution version
echo "Solution Version Creating... It will takes no longer than 6 hours..."
MAX_TIME=`expr 6 \* 60 \* 60` # 6 hours
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    ranking_solution_version_status=$(aws personalize describe-solution-version \
            --solution-version-arn ${ranking_solution_version_arn} | jq '.solutionVersion.status' -r)
            
    echo "ranking_solution_version_status: ${ranking_solution_version_status}"
    
    if [ "$ranking_solution_version_status" = "CREATE FAILED" ]
    then
        echo "!!!Ranking Solution Version Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [ "$ranking_solution_version_status" = "ACTIVE" ]
    then
        echo "Ranking Solution Version create successfully!"
        break;
    fi
    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Ranking Solution Version Time exceed 10 min, please delete Ranking Solution Version and try again!"
    exit 8
fi


# create event tracker
eventTrackerArn=$(aws personalize create-event-tracker \
    --name NewsRankingEventTracker \
    --dataset-group-arn ${datasetGroupArn} | jq '.eventTrackerArn' -r)

trackingId=$(aws personalize describe-event-tracker \
    --event-tracker-arn ${eventTrackerArn} | jq '.eventTracker.trackingId' -r)
    
echo "eventTrackerArn: ${eventRankingTrackerArn}"
echo "trackingId: ${trackingId}"

# # for test
# userPersonalize_solution_version_arn="arn:aws:personalize:ap-northeast-1:466154167985:solution/userPersonalizeSolution/e98f9f3c"

#print metrics
echo "Ranking Solution Metrics:"
aws personalize get-solution-metrics --solution-version-arn ${ranking_solution_version_arn}


#create campaign
ranking_campaign_arn=$(aws personalize create-campaign \
        --name gcr-rs-dev-workshop-news-ranking-campaign \
        --solution-version-arn ${ranking_solution_version_arn} \
        --min-provisioned-tps 1 --output text)


#monitor campaign
echo "Campaign Creating... It will takes no longer than 3 hours..."
MAX_TIME=`expr 3 \* 60 \* 60` # 3 hours
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    ranking_campaign_status=$(aws personalize describe-campaign \
            --campaign-arn ${ranking_campaign_arn} | jq '.campaign.status' -r)
            
    echo "ranking_campaign_status: ${ranking_campaign_status}"
    
    if [ "$ranking_campaign_status" = "CREATE FAILED" ]
    then
        echo "!!!Ranking Campaign Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [ "$ranking_campaign_status" = "ACTIVE" ]
    then
        echo "Ranking Campaign create successfully!"
        break;
    fi
    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Ranking Campaign Time exceed 10 min, please delete Ranking Campaign and try again!"
    exit 8
fi


echo "Congratulations!!! Your AWS Personalize Service Create Successfully!!!"







    
    
    


	



