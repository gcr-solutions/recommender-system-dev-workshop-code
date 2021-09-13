#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

echo "--------start creating personalize role ----------"
./create-personalize-role.sh $1

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

Scenario=$2

if [[ -z $Scenario ]];then
    Scenario='News'
fi

if [[ -z $METHOD ]];then
    METHOD='customize'
fi


AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"


BUCKET_BUILD=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=sample-data-news

echo "Stage=$Stage"
echo "REGION=$REGION"
echo "Scenario=$Scenario"
echo "METHOD=$METHOD"
echo "BUCKET=${BUCKET_BUILD}"
echo "Prefix=${PREFIX}"

#create dataset group
datasetGroupArn="arn:aws:personalize:us-east-1:466154167985:dataset-group/GCR-RS-News-Dataset-Group"
#datasetGroupArn=$($AWS_CMD personalize create-dataset-group --name GCR-RS-${Scenario}-Dataset-Group --output text)
echo "dataset_Group_Arn: ${datasetGroupArn}"
echo "......"

#monitor dataset group
echo "Dataset Group Creating... It will takes no longer than 5 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} ))
do
    dataset_group_status=$($AWS_CMD personalize describe-dataset-group \
                --dataset-group-arn ${datasetGroupArn} | jq '.datasetGroup.status' -r)

    echo "dataset_group_status: ${dataset_group_status}"

    if [ "$dataset_group_status" = "CREATE FAILED" ]
    then
        echo "!!!Dataset Group Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [ "$dataset_group_status" = "ACTIVE" ]
    then
        echo "Dataset Group Create successfully!"
        break
    fi

    CURRENT_TIME=`expr ${CURRENT_TIME} + 10`
    echo "wait for 10 second..."
    sleep 10

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Dataset Group Create Time exceed 5 min, please delete import job and try again!"
    exit 8
fi


#create schema
echo "creating Schema..."
user_schema_arn="arn:aws:personalize:us-east-1:466154167985:schema/NewsUserSchema"
#user_schema_arn=$($AWS_CMD personalize create-schema \
#	--name ${Scenario}UserSchema \
#	--schema file://./schema/${Scenario}UserSchema.json --output text)

item_schema_arn="arn:aws:personalize:us-east-1:466154167985:schema/NewsItemSchema"
#item_schema_arn=$($AWS_CMD personalize create-schema \
#	--name ${Scenario}ItemSchema \
#	--schema file://./schema/${Scenario}ItemSchema.json --output text)

interaction_schema_arn="arn:aws:personalize:us-east-1:466154167985:schema/NewsInteractionSchema"
#interaction_schema_arn=$($AWS_CMD personalize create-schema \
#	--name ${Scenario}InteractionSchema \
#	--schema file://./schema/${Scenario}InteractionSchema.json --output text)

#echo "......"
#sleep 30

#create dataset
echo "create dataset..."
user_dataset_arn=$($AWS_CMD personalize create-dataset \
	--name ${Scenario}UserDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Users \
	--schema-arn ${user_schema_arn} --output text)

item_dataset_arn=$($AWS_CMD personalize create-dataset \
	--name ${Scenario}ItemDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Items \
	--schema-arn ${item_schema_arn} --output text)

interaction_dataset_arn=$($AWS_CMD personalize create-dataset \
	--name ${Scenario}InteractionDataset \
	--dataset-group-arn ${datasetGroupArn} \
	--dataset-type Interactions \
	--schema-arn ${interaction_schema_arn} --output text)


#monitor dataset
echo "Dataset Creating... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} ))
do
    user_dataset_status=$($AWS_CMD personalize describe-dataset \
                --dataset-arn ${user_dataset_arn} | jq '.dataset.status' -r)
    item_dataset_status=$($AWS_CMD personalize describe-dataset \
                --dataset-arn ${item_dataset_arn} | jq '.dataset.status' -r)
    interaction_dataset_status=$($AWS_CMD personalize describe-dataset \
                --dataset-arn ${interaction_dataset_arn} | jq '.dataset.status' -r)

    echo "user_dataset_status: ${user_dataset_status}"
    echo "item_dataset_status: ${item_dataset_status}"
    echo "interaction_dataset_status: ${interaction_dataset_status}"

    if [[ "$user_dataset_status" = "CREATE FAILED" || "$item_dataset_status" = "CREATE FAILED" || "$interaction_dataset_status" = "CREATE FAILED" ]]
    then
        echo "!!!Dataset Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ "$user_dataset_status" = "ACTIVE" && "$item_dataset_status" = "ACTIVE" && "$interaction_dataset_status" = "ACTIVE" ]]
    then
        echo "Dataset Create successfully!"
        break
    fi

    CURRENT_TIME=`expr ${CURRENT_TIME} + 10`
    echo "wait for 10 second..."
    sleep 10

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Dataset Create Time exceed 10 min, please delete import job and try again!"
    exit 8
fi



PERSONALIZE_ROLE_BUILD=arn:aws:iam::${AWS_ACCOUNT_ID}:role/gcr-rs-personalize-role
echo "PERSONALIZE_ROLE_BUILD=${PERSONALIZE_ROLE_BUILD}"
echo "Check if your personalize role arn is equal to the PERSONALIZE_ROLE_BUILD. If not, please follow the previous step to create iam role for personalize!"



#create import job
echo "create dataset import job..."
user_dataset_import_job_arn=$($AWS_CMD personalize create-dataset-import-job \
  --job-name ${Scenario}UserImportJob \
  --dataset-arn ${user_dataset_arn} \
  --data-source dataLocation=s3://${BUCKET_BUILD}/${PREFIX}/system/ps-ingest-data/user/ps_user.csv \
  --role-arn ${PERSONALIZE_ROLE_BUILD} \
  --output text)


item_dataset_import_job_arn=$($AWS_CMD personalize create-dataset-import-job \
  --job-name ${Scenario}ItemImportJob \
  --dataset-arn ${item_dataset_arn} \
  --data-source dataLocation=s3://${BUCKET_BUILD}/${PREFIX}/system/ps-ingest-data/item/ps_item.csv \
  --role-arn ${PERSONALIZE_ROLE_BUILD} \
  --output text)

interaction_dataset_import_job_arn=$($AWS_CMD personalize create-dataset-import-job \
  --job-name ${Scenario}InteractionImportJob \
  --dataset-arn ${interaction_dataset_arn} \
  --data-source dataLocation=s3://${BUCKET_BUILD}/${PREFIX}/system/ps-ingest-data/action/ps_action.csv \
  --role-arn ${PERSONALIZE_ROLE_BUILD} \
  --output text)

echo "......"


#monitor import job
echo "Data Importing... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} ))
do
    user_dataset_import_job_status=$($AWS_CMD personalize describe-dataset-import-job \
                --dataset-import-job-arn ${user_dataset_import_job_arn} | jq '.datasetImportJob.status' -r)
    item_dataset_import_job_status=$($AWS_CMD personalize describe-dataset-import-job \
                --dataset-import-job-arn ${item_dataset_import_job_arn} | jq '.datasetImportJob.status' -r)
    interaction_dataset_import_job_status=$($AWS_CMD personalize describe-dataset-import-job \
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


##code for only need one method
#solution_arn=""
#if [[ $METHOD == "UserPersonalize" ]]; then
#    solution_arn=$(aws personalize create-solution \
#          --name ${METHOD}Solution \
#          --dataset-group-arn ${datasetGroupArn} \
#          --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization --output text)
#elif [[ $METHOD == "Ranking" ]]; then
#    solution_arn=$(aws personalize create-solution \
#          --name ${METHOD}Solution \
#          --dataset-group-arn ${datasetGroupArn} \
#          --recipe-arn arn:aws:personalize:::recipe/aws-personalized-ranking --output text)
#elif [[ $METHOD == "Sims" ]]; then
#    solution_arn=$(aws personalize create-solution \
#          --name ${METHOD}Solution \
#          --dataset-group-arn ${datasetGroupArn} \
#          --recipe-arn arn:aws:personalize:::recipe/aws-sims --output text)
#fi
#


#create solutions for 3 methods
userPersonalize_solution_arn=$($AWS_CMD personalize create-solution \
        --name UserPersonalizeSolution \
        --dataset-group-arn ${datasetGroupArn} \
        --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization --output text)

ranking_solution_arn=$($AWS_CMD personalize create-solution \
        --name RankingSolution \
        --dataset-group-arn ${datasetGroupArn} \
        --recipe-arn arn:aws:personalize:::recipe/aws-personalized-ranking --output text)

sims_solution_arn=$($AWS_CMD personalize create-solution \
        --name SimsSolution \
        --dataset-group-arn ${datasetGroupArn} \
        --recipe-arn arn:aws:personalize:::recipe/aws-sims --output text)


#monitor solution
echo "Solution Creating... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} ))
do
    userPersonalize_solution_status=$($AWS_CMD personalize describe-solution \
        --solution-arn ${userPersonalize_solution_arn} | jq '.solution.status' -r)
    ranking_solution_status=$($AWS_CMD personalize describe-solution \
        --solution-arn ${ranking_solution_arn} | jq '.solution.status' -r)
    sims_solution_status=$($AWS_CMD personalize describe-solution \
        --solution-arn ${sims_solution_arn} | jq '.solution.status' -r)

    echo "userPersonalize_solution_status: ${userPersonalize_solution_status}"
    echo "ranking_solution_status: ${ranking_solution_status}"
    echo "sims_solution_status: ${sims_solution_status}"


    if [[ "$userPersonalize_solution_status" = "CREATE FAILED" || "$ranking_solution_status" = "CREATE FAILED" || "$sims_solution_status" = "CREATE FAILED" ]]
    then
        echo "!!!Solutions Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ "$userPersonalize_solution_status" = "ACTIVE" && "$ranking_solution_status" = "ACTIVE" && "$sims_solution_status" = "ACTIVE" ]]
    then
        echo "Solutions create successfully!"
        break;
    fi
    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Solutions Time exceed 10 min, please delete Solution and try again!"
    exit 8
fi



#create solution version
userPersonalize_solution_version_arn=$($AWS_CMD personalize create-solution-version \
        --solution-arn ${userPersonalize_solution_arn} --output text)
ranking_solution_version_arn=$($AWS_CMD personalize create-solution-version \
        --solution-arn ${ranking_solution_arn} --output text)
sims_solution_version_arn=$($AWS_CMD personalize create-solution-version \
        --solution-arn ${sims_solution_arn} --output text)

#monitor solution version
echo "Solution Version Creating... It will takes no longer than 2 hours..."
MAX_TIME=`expr 2 \* 60 \* 60` # 6 hours
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} ))
do
    userPersonalize_solution_version_status=$($AWS_CMD personalize describe-solution-version \
            --solution-version-arn ${userPersonalize_solution_version_arn} | jq '.solutionVersion.status' -r)
    ranking_solution_version_status=$($AWS_CMD personalize describe-solution-version \
            --solution-version-arn ${ranking_solution_version_arn} | jq '.solutionVersion.status' -r)
    sims_solution_version_status=$($AWS_CMD personalize describe-solution-version \
            --solution-version-arn ${sims_solution_version_arn} | jq '.solutionVersion.status' -r)

    echo "userPersonalize_solution_version_status: ${userPersonalize_solution_version_status}"
    echo "ranking_solution_version_status: ${ranking_solution_version_status}"
    echo "sims_solution_version_status: ${sims_solution_version_status}"

    if [[ "$userPersonalize_solution_version_status" = "CREATE FAILED" || "$ranking_solution_version_status" = "CREATE FAILED" || "$sims_solution_version_status" = "CREATE FAILED" ]]
    then
        echo "!!!Solution Version Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ "$userPersonalize_solution_version_status" = "ACTIVE" && "$ranking_solution_version_status" = "ACTIVE" && "$sims_solution_version_status" = "ACTIVE" ]]
    then
        echo "Solution Version create successfully!"
        break;
    fi
    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Solution Versions Time exceed 2 hours, please delete UserPersonalize Solution Version and try again!"
    exit 8
fi


# create event tracker
eventTrackerArn=$($AWS_CMD personalize create-event-tracker \
    --name NewsEventTracker \
    --dataset-group-arn ${datasetGroupArn} | jq '.eventTrackerArn' -r)

trackingId=$($AWS_CMD personalize describe-event-tracker \
    --event-tracker-arn ${eventTrackerArn} | jq '.eventTracker.trackingId' -r)
    
echo "eventTrackerArn: ${eventTrackerArn}"
echo "trackingId: ${trackingId}"


#print metrics
echo "UserPersonalize Solution Metrics:"
aws personalize get-solution-metrics --solution-version-arn ${userPersonalize_solution_version_arn}
echo "Ranking Solution Metrics:"
aws personalize get-solution-metrics --solution-version-arn ${ranking_solution_version_arn}
echo "Sims Solution Metrics:"
aws personalize get-solution-metrics --solution-version-arn ${sims_solution_version_arn}

#create campaign
userPersonalize_campaign_arn=$($AWS_CMD personalize create-campaign \
        --name gcr-rs-${Stage}-news-UserPersonalize-campaign \
        --solution-version-arn ${userPersonalize_solution_version_arn} \
        --min-provisioned-tps 1 --output text)
ranking_campaign_arn=$($AWS_CMD personalize create-campaign \
        --name gcr-rs-${Stage}-news-Ranking-campaign \
        --solution-version-arn ${ranking_solution_version_arn} \
        --min-provisioned-tps 1 --output text)
sims_campaign_arn=$($AWS_CMD personalize create-campaign \
        --name gcr-rs-${Stage}-news-Sims-campaign \
        --solution-version-arn ${sims_solution_version_arn} \
        --min-provisioned-tps 1 --output text)


#monitor campaign
echo "Campaign Creating... It will takes no longer than 1 hours..."
MAX_TIME=`expr 1 \* 60 \* 60` # 1 hours
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    userPersonalize_campaign_status=$($AWS_CMD personalize describe-campaign \
            --campaign-arn ${userPersonalize_campaign_arn} | jq '.campaign.status' -r)
    ranking_campaign_status=$($AWS_CMD personalize describe-campaign \
            --campaign-arn ${ranking_campaign_arn} | jq '.campaign.status' -r)
    sims_campaign_status=$($AWS_CMD personalize describe-campaign \
            --campaign-arn ${sims_campaign_arn} | jq '.campaign.status' -r)
            
    echo "userPersonalize_campaign_status: ${userPersonalize_campaign_status}"
    echo "ranking_campaign_status: ${ranking_campaign_status}"
    echo "sims_campaign_status: ${sims_campaign_status}"

    
    if [[ "$userPersonalize_campaign_status" = "CREATE FAILED" || "$ranking_campaign_status" = "CREATE FAILED" || "$sims_campaign_status" = "CREATE FAILED" ]]
    then
        echo "!!!Campaign Create Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ "$userPersonalize_campaign_status" = "ACTIVE" && "$ranking_campaign_status" = "ACTIVE" && "$sims_campaign_status" = "ACTIVE" ]]
    then
        echo "Campaign create successfully!"
        break;
    fi
    CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
    echo "wait for 1 min..."
    sleep 60

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Campaigns Time exceed 1 hour, please delete UserPersonalize Campaign and try again!"
    exit 8
fi

echo "Update ps_config.json ..."
config_file_path="./ps_config.json"
sed -e "s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
            ./ps_config_template.json > ${config_file_path}

old_event_track_arn=$(awk -F"\"" '/EventTrackerArn/{print $4}' $config_file_path)
echo "change old_event_track_arn: ${old_event_track_arn} to new_event_track_arn: ${eventTrackerArn}"
sed -e "s@$old_event_track_arn@$eventTrackerArn@g" -i $config_file_path

old_event_track_id=$(awk -F"\"" '/EventTrackerId/{print $4}' $config_file_path)
echo "change old_event_track_id: ${old_event_track_id} to new_event_track_id: ${EventTrackerId}"
sed -e "s@$old_event_track_id@$EventTrackerId@g" -i $config_file_path

cp ./ps_config.json ../../sample-data/system/ps-config/ps_config.json

rm -f ./ps_config.json

echo "Congratulations. Your AWS Personalize Service Create Successfully."

