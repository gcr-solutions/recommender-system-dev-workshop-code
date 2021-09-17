#!/usr/bin/env bash
set -e

curr_dir=$(pwd)
echo "==============Create Personalize======================"

METHOD=$1
if [[ -z $METHOD ]];then
    METHOD='all'
fi

Stage=$2
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

Scenario=$3

if [[ -z $Scenario ]];then
    Scenario='News'
fi


AWS_P="aws"
if [[ $REGION =~ cn.* ]];then
  AWS_P="aws-cn"
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

if [[ "${METHOD}" != "ps-complete" && "${METHOD}" != "ps-rank" && "${METHOD}" != "ps-sims" && "${METHOD}" != "all" ]]; then
  echo "-----Type Wrong Method. You can enter ps-complete or ps-rank or ps-sims or all-------"
  exit 1
fi

echo "--------start creating personalize role ----------"
./create-personalize-role.sh $Stage

PERSONALIZE_ROLE_BUILD=arn:${AWS_P}:iam::${AWS_ACCOUNT_ID}:role/gcr-rs-personalize-role
echo "PERSONALIZE_ROLE_BUILD=${PERSONALIZE_ROLE_BUILD}"
echo "Check if your personalize role arn is equal to the PERSONALIZE_ROLE_BUILD. If not, please follow the previous step to create iam role for personalize!"


#create dataset group
datasetGroupArn=$($AWS_CMD personalize list-dataset-groups --region $REGION | jq '.[][] | select(.name=="GCR-RS-News-Dataset-Group")' | jq '.datasetGroupArn' -r)
if [[ "${datasetGroupArn}" != "" ]]; then
  echo "Dataset Group Already Exist"
else
  datasetGroupArn=$($AWS_CMD personalize create-dataset-group --region $REGION --name GCR-RS-${Scenario}-Dataset-Group --output text)

  #monitor dataset group
  echo "Dataset Group Creating... It will takes no longer than 5 min..."
  MAX_TIME=`expr 10 \* 60` # 10 min
  CURRENT_TIME=0
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      dataset_group_status=$($AWS_CMD personalize describe-dataset-group --region $REGION \
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

fi

echo "dataset_Group_Arn: ${datasetGroupArn}"
echo "------------------------------------------------"


#create schema
echo "creating Schema..."
user_schema_arn=$($AWS_CMD personalize list-schemas --region $REGION | jq '.[][] | select(.name=="NewsUserSchema")' | jq '.schemaArn' -r)
if [[ "${user_schema_arn}" == "" ]]; then
  user_schema_arn=$($AWS_CMD personalize create-schema --region $REGION \
    --name ${Scenario}UserSchema \
    --schema file://./schema/${Scenario}UserSchema.json --output text)
fi

item_schema_arn=$($AWS_CMD personalize list-schemas --region $REGION | jq '.[][] | select(.name=="NewsItemSchema")' | jq '.schemaArn' -r)
if [[ "${item_schema_arn}" == "" ]]; then
  item_schema_arn=$($AWS_CMD personalize create-schema --region $REGION \
    --name ${Scenario}ItemSchema \
    --schema file://./schema/${Scenario}ItemSchema.json --output text)
fi

interaction_schema_arn=$($AWS_CMD personalize list-schemas --region $REGION | jq '.[][] | select(.name=="NewsInteractionSchema")' | jq '.schemaArn' -r)
if [[ "${interaction_schema_arn}" == "" ]]; then
  interaction_schema_arn=$($AWS_CMD personalize create-schema --region $REGION \
    --name ${Scenario}InteractionSchema \
    --schema file://./schema/${Scenario}InteractionSchema.json --output text)
fi


sleep 30
echo "------------------------------------------------"

#create dataset
echo "create dataset..."
user_dataset_arn=$($AWS_CMD personalize list-datasets --region $REGION --dataset-group-arn $datasetGroupArn | jq \
                                            '.datasets[] | select(.name=="NewsUserDataset")' | jq '.datasetArn' -r)
if [[ "${user_dataset_arn}" == "" ]]; then
  user_dataset_arn=$($AWS_CMD personalize create-dataset --region $REGION \
    --name ${Scenario}UserDataset \
    --dataset-group-arn ${datasetGroupArn} \
    --dataset-type Users \
    --schema-arn ${user_schema_arn} --output text)
fi

item_dataset_arn=$($AWS_CMD personalize list-datasets --region $REGION --dataset-group-arn $datasetGroupArn | jq \
                                            '.datasets[] | select(.name=="NewsItemDataset")' | jq '.datasetArn' -r)
if [[ "${item_dataset_arn}" == "" ]]; then
  item_dataset_arn=$($AWS_CMD personalize create-dataset --region $REGION \
    --name ${Scenario}ItemDataset \
    --dataset-group-arn ${datasetGroupArn} \
    --dataset-type Items \
    --schema-arn ${item_schema_arn} --output text)
fi

interaction_dataset_arn=$($AWS_CMD personalize list-datasets --region $REGION --dataset-group-arn $datasetGroupArn | jq \
                                            '.datasets[] | select(.name=="NewsInteractionDataset")' | jq '.datasetArn' -r)
if [[ "${interaction_dataset_arn}" == "" ]]; then
  interaction_dataset_arn=$($AWS_CMD personalize create-dataset --region $REGION \
    --name ${Scenario}InteractionDataset \
    --dataset-group-arn ${datasetGroupArn} \
    --dataset-type Interactions \
    --schema-arn ${interaction_schema_arn} --output text)
fi

#monitor dataset
echo "Dataset Creating... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} ))
do
    user_dataset_status=$($AWS_CMD personalize describe-dataset --region $REGION \
                --dataset-arn ${user_dataset_arn} | jq '.dataset.status' -r)
    item_dataset_status=$($AWS_CMD personalize describe-dataset --region $REGION \
                --dataset-arn ${item_dataset_arn} | jq '.dataset.status' -r)
    interaction_dataset_status=$($AWS_CMD personalize describe-dataset --region $REGION \
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

echo "------------------------------------------------"

#create import job
echo "create dataset import job..."
user_dataset_import_job_arn=$($AWS_CMD personalize list-dataset-import-jobs --region $REGION --dataset-arn $user_dataset_arn \
                                      | jq '.datasetImportJobs[] | select(.jobName=="NewsUserImportJob")' | jq '.datasetImportJobArn' -r)
if [[ "${user_dataset_import_job_arn}" == "" ]]; then
  user_dataset_import_job_arn=$($AWS_CMD personalize create-dataset-import-job --region $REGION \
    --job-name ${Scenario}UserImportJob \
    --dataset-arn ${user_dataset_arn} \
    --data-source dataLocation=s3://${BUCKET_BUILD}/${PREFIX}/system/ps-ingest-data/user/ps_user.csv \
    --role-arn ${PERSONALIZE_ROLE_BUILD} \
    --output text)
fi

item_dataset_import_job_arn=$($AWS_CMD personalize list-dataset-import-jobs --region $REGION --dataset-arn $item_dataset_arn \
                                      | jq '.datasetImportJobs[] | select(.jobName=="NewsItemImportJob")' | jq '.datasetImportJobArn' -r)
if [[ "${item_dataset_import_job_arn}" == "" ]]; then
  item_dataset_import_job_arn=$($AWS_CMD personalize create-dataset-import-job --region $REGION \
    --job-name ${Scenario}ItemImportJob \
    --dataset-arn ${item_dataset_arn} \
    --data-source dataLocation=s3://${BUCKET_BUILD}/${PREFIX}/system/ps-ingest-data/item/ps_item.csv \
    --role-arn ${PERSONALIZE_ROLE_BUILD} \
    --output text)
fi

interaction_dataset_import_job_arn=$($AWS_CMD personalize list-dataset-import-jobs --region $REGION --dataset-arn $interaction_dataset_arn \
                                      | jq '.datasetImportJobs[] | select(.jobName=="NewsInteractionImportJob")' | jq '.datasetImportJobArn' -r)
if [[ "${interaction_dataset_import_job_arn}" == "" ]]; then
  interaction_dataset_import_job_arn=$($AWS_CMD personalize create-dataset-import-job --region $REGION \
    --job-name ${Scenario}InteractionImportJob \
    --dataset-arn ${interaction_dataset_arn} \
    --data-source dataLocation=s3://${BUCKET_BUILD}/${PREFIX}/system/ps-ingest-data/action/ps_action.csv \
    --role-arn ${PERSONALIZE_ROLE_BUILD} \
    --output text)
fi



#monitor import job
echo "Data Importing... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} ))
do
    user_dataset_import_job_status=$($AWS_CMD personalize describe-dataset-import-job --region $REGION \
                --dataset-import-job-arn ${user_dataset_import_job_arn} | jq '.datasetImportJob.status' -r)
    item_dataset_import_job_status=$($AWS_CMD personalize describe-dataset-import-job --region $REGION \
                --dataset-import-job-arn ${item_dataset_import_job_arn} | jq '.datasetImportJob.status' -r)
    interaction_dataset_import_job_status=$($AWS_CMD personalize describe-dataset-import-job --region $REGION \
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

echo "------------------------------------------------"

#create solutions for 3 methods
userPersonalize_solution_arn=$($AWS_CMD personalize list-solutions --region $REGION --dataset-group-arn $datasetGroupArn | \
                                jq '.solutions[] | select(.name=="UserPersonalizeSolution")' | jq '.solutionArn' -r)
ranking_solution_arn=$($AWS_CMD personalize list-solutions --region $REGION --dataset-group-arn $datasetGroupArn | \
                                jq '.solutions[] | select(.name=="RankingSolution")' | jq '.solutionArn' -r)
sims_solution_arn=$($AWS_CMD personalize list-solutions --region $REGION --dataset-group-arn $datasetGroupArn | \
                                jq '.solutions[] | select(.name=="SimsSolution")' | jq '.solutionArn' -r)
if [[ $METHOD == "ps-complete" ]]; then
  if [[ "${userPersonalize_solution_arn}" == "" ]]; then
    userPersonalize_solution_arn=$($AWS_CMD personalize create-solution --region $REGION \
            --name UserPersonalizeSolution \
            --dataset-group-arn ${datasetGroupArn} \
            --recipe-arn arn:${AWS_P}:personalize:::recipe/aws-user-personalization --output text)
  fi
elif [[ $METHOD == "ps-rank" ]]; then
  if [[ "${ranking_solution_arn}" == "" ]]; then
    ranking_solution_arn=$($AWS_CMD personalize create-solution --region $REGION \
            --name RankingSolution \
            --dataset-group-arn ${datasetGroupArn} \
            --recipe-arn arn:${AWS_P}:personalize:::recipe/aws-personalized-ranking --output text)
  fi
elif [[ $METHOD == "ps-sims" ]]; then
  if [[ "${sims_solution_arn}" == "" ]]; then
    sims_solution_arn=$($AWS_CMD personalize create-solution --region $REGION \
            --name SimsSolution \
            --dataset-group-arn ${datasetGroupArn} \
            --recipe-arn arn:${AWS_P}:personalize:::recipe/aws-sims --output text)
  fi
else
  if [[ "${userPersonalize_solution_arn}" == "" ]]; then
    userPersonalize_solution_arn=$($AWS_CMD personalize create-solution --region $REGION \
            --name UserPersonalizeSolution \
            --dataset-group-arn ${datasetGroupArn} \
            --recipe-arn arn:${AWS_P}:personalize:::recipe/aws-user-personalization --output text)
  fi

  if [[ "${ranking_solution_arn}" == "" ]]; then
    ranking_solution_arn=$($AWS_CMD personalize create-solution --region $REGION \
            --name RankingSolution \
            --dataset-group-arn ${datasetGroupArn} \
            --recipe-arn arn:${AWS_P}:personalize:::recipe/aws-personalized-ranking --output text)
  fi

  if [[ "${sims_solution_arn}" == "" ]]; then
    sims_solution_arn=$($AWS_CMD personalize create-solution --region $REGION \
            --name SimsSolution \
            --dataset-group-arn ${datasetGroupArn} \
            --recipe-arn arn:${AWS_P}:personalize:::recipe/aws-sims --output text)
  fi
fi


#monitor solution
echo "Solution Creating... It will takes no longer than 10 min..."
MAX_TIME=`expr 10 \* 60` # 10 min
CURRENT_TIME=0
if [[ $METHOD == "ps-complete" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      userPersonalize_solution_status=$($AWS_CMD personalize describe-solution --region $REGION \
          --solution-arn ${userPersonalize_solution_arn} | jq '.solution.status' -r)

      echo "userPersonalize_solution_status: ${userPersonalize_solution_status}"

      if [[ "$userPersonalize_solution_status" = "CREATE FAILED" ]]
      then
          echo "!!!Solutions Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$userPersonalize_solution_status" = "ACTIVE" ]]
      then
          echo "Solutions create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
elif [[ $METHOD == "ps-rank" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      ranking_solution_status=$($AWS_CMD personalize describe-solution --region $REGION \
          --solution-arn ${ranking_solution_arn} | jq '.solution.status' -r)

      echo "ranking_solution_status: ${ranking_solution_status}"

      if [[ "$ranking_solution_status" = "CREATE FAILED" ]]
      then
          echo "!!!Solutions Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$ranking_solution_status" = "ACTIVE" ]]
      then
          echo "Solutions create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
elif [[ $METHOD == "ps-sims" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      sims_solution_status=$($AWS_CMD personalize describe-solution --region $REGION \
          --solution-arn ${sims_solution_arn} | jq '.solution.status' -r)

      echo "sims_solution_status: ${sims_solution_status}"

      if [[ "$sims_solution_status" == "CREATE FAILED" ]]
      then
          echo "!!!Solutions Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$sims_solution_status" == "ACTIVE" ]]
      then
          echo "Solutions create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
else
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      userPersonalize_solution_status=$($AWS_CMD personalize describe-solution --region $REGION \
          --solution-arn ${userPersonalize_solution_arn} | jq '.solution.status' -r)
      ranking_solution_status=$($AWS_CMD personalize describe-solution --region $REGION \
          --solution-arn ${ranking_solution_arn} | jq '.solution.status' -r)
      sims_solution_status=$($AWS_CMD personalize describe-solution --region $REGION \
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
fi

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Solutions Time exceed 10 min, please delete Solution and try again!"
    exit 8
fi



#create solution version
if [[ $METHOD == "ps-complete" ]]; then
  userPersonalize_solution_version_arn=$($AWS_CMD personalize create-solution-version --region $REGION \
          --solution-arn ${userPersonalize_solution_arn} --output text)
elif [[ $METHOD == "ps-rank" ]]; then
  ranking_solution_version_arn=$($AWS_CMD personalize create-solution-version --region $REGION \
          --solution-arn ${ranking_solution_arn} --output text)
elif [[ $METHOD == "ps-sims" ]]; then
  sims_solution_version_arn=$($AWS_CMD personalize create-solution-version --region $REGION \
          --solution-arn ${sims_solution_arn} --output text)
else
  userPersonalize_solution_version_arn=$($AWS_CMD personalize create-solution-version --region $REGION \
          --solution-arn ${userPersonalize_solution_arn} --output text)
  ranking_solution_version_arn=$($AWS_CMD personalize create-solution-version --region $REGION \
          --solution-arn ${ranking_solution_arn} --output text)
  sims_solution_version_arn=$($AWS_CMD personalize create-solution-version --region $REGION \
          --solution-arn ${sims_solution_arn} --output text)
fi

#monitor solution version
echo "Solution Version Creating... It will takes no longer than 2 hours..."
MAX_TIME=`expr 2 \* 60 \* 60` # 6 hours
CURRENT_TIME=0
if [[ $METHOD == "ps-complete" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      userPersonalize_solution_version_status=$($AWS_CMD personalize describe-solution-version --region $REGION \
              --solution-version-arn ${userPersonalize_solution_version_arn} | jq '.solutionVersion.status' -r)

      echo "userPersonalize_solution_version_status: ${userPersonalize_solution_version_status}"

      if [[ "$userPersonalize_solution_version_status" = "CREATE FAILED" ]]
      then
          echo "!!!Solution Version Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$userPersonalize_solution_version_status" = "ACTIVE" ]]
      then
          echo "Solution Version create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
elif [[ $METHOD == "ps-rank" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      ranking_solution_version_status=$($AWS_CMD personalize describe-solution-version --region $REGION \
              --solution-version-arn ${ranking_solution_version_arn} | jq '.solutionVersion.status' -r)

      echo "ranking_solution_version_status: ${ranking_solution_version_status}"

      if [[ "$ranking_solution_version_status" = "CREATE FAILED" ]]
      then
          echo "!!!Solution Version Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$ranking_solution_version_status" = "ACTIVE" ]]
      then
          echo "Solution Version create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
elif [[ $METHOD == "ps-sims" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      sims_solution_version_status=$($AWS_CMD personalize describe-solution-version --region $REGION \
              --solution-version-arn ${sims_solution_version_arn} | jq '.solutionVersion.status' -r)

      echo "sims_solution_version_status: ${sims_solution_version_status}"

      if [[ "$sims_solution_version_status" = "CREATE FAILED" ]]
      then
          echo "!!!Solution Version Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$sims_solution_version_status" = "ACTIVE" ]]
      then
          echo "Solution Version create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
else
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      userPersonalize_solution_version_status=$($AWS_CMD personalize describe-solution-version --region $REGION \
              --solution-version-arn ${userPersonalize_solution_version_arn} | jq '.solutionVersion.status' -r)
      ranking_solution_version_status=$($AWS_CMD personalize describe-solution-version --region $REGION \
              --solution-version-arn ${ranking_solution_version_arn} | jq '.solutionVersion.status' -r)
      sims_solution_version_status=$($AWS_CMD personalize describe-solution-version --region $REGION \
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
fi


if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Solution Versions Time exceed 2 hours, please delete UserPersonalize Solution Version and try again!"
    exit 8
fi


# create event tracker
eventTrackerArn=$($AWS_CMD personalize list-event-trackers --region $REGION --dataset-group-arn $datasetGroupArn | \
                    jq '.eventTrackers[] | select(.name=="NewsEventTracker")' | jq '.eventTrackerArn' -r)
if [[ "${eventTrackerArn}" == "" ]]; then
  eventTrackerArn=$($AWS_CMD personalize create-event-tracker --region $REGION \
      --name NewsEventTracker \
      --dataset-group-arn ${datasetGroupArn} | jq '.eventTrackerArn' -r)
fi

trackingId=$($AWS_CMD personalize describe-event-tracker --region $REGION \
    --event-tracker-arn ${eventTrackerArn} | jq '.eventTracker.trackingId' -r)
    
echo "eventTrackerArn: ${eventTrackerArn}"
echo "trackingId: ${trackingId}"


#print metrics
if [[ $METHOD == "ps-complete" ]]; then
  echo "UserPersonalize Solution Metrics:"
  aws personalize get-solution-metrics --region $REGION --solution-version-arn ${userPersonalize_solution_version_arn}
elif [[ $METHOD == "ps-rank" ]]; then
  echo "Ranking Solution Metrics:"
  aws personalize get-solution-metrics --region $REGION --solution-version-arn ${ranking_solution_version_arn}
elif [[ $METHOD == "ps-sims" ]]; then
  echo "Sims Solution Metrics:"
  aws personalize get-solution-metrics --region $REGION --solution-version-arn ${sims_solution_version_arn}
else
  echo "UserPersonalize Solution Metrics:"
  aws personalize get-solution-metrics --region $REGION --solution-version-arn ${userPersonalize_solution_version_arn}
  echo "Ranking Solution Metrics:"
  aws personalize get-solution-metrics --region $REGION --solution-version-arn ${ranking_solution_version_arn}
  echo "Sims Solution Metrics:"
  aws personalize get-solution-metrics --region $REGION --solution-version-arn ${sims_solution_version_arn}
fi

#create campaign
if [[ $METHOD == "ps-complete" ]]; then
  userPersonalize_campaign_arn=$($AWS_CMD personalize list-campaigns --region $REGION --solution-arn $userPersonalize_solution_arn | \
                                jq '.campaigns[] | select(.name=="gcr-rs-dev-workshop-news-UserPersonalize-campaign")' | \
                                jq '.campaignArn' -r)
  if [[ "${userPersonalize_campaign_arn}" == "" ]]; then
    userPersonalize_campaign_arn=$($AWS_CMD personalize create-campaign --region $REGION \
            --name gcr-rs-${Stage}-news-UserPersonalize-campaign \
            --solution-version-arn ${userPersonalize_solution_version_arn} \
            --min-provisioned-tps 1 --output text)
  fi
elif [[ $METHOD == "ps-rank" ]]; then
  ranking_campaign_arn=$($AWS_CMD personalize list-campaigns --region $REGION --solution-arn $ranking_solution_arn | \
                                jq '.campaigns[] | select(.name=="gcr-rs-dev-workshop-news-Ranking-campaign")' | \
                                jq '.campaignArn' -r)
  if [[ "${ranking_campaign_arn}" == "" ]]; then
    ranking_campaign_arn=$($AWS_CMD personalize create-campaign --region $REGION \
            --name gcr-rs-${Stage}-news-Ranking-campaign \
            --solution-version-arn ${ranking_solution_version_arn} \
            --min-provisioned-tps 1 --output text)
  fi
elif [[ $METHOD == "ps-sims" ]]; then
  sims_campaign_arn=$($AWS_CMD personalize list-campaigns --region $REGION --solution-arn $sims_solution_arn | \
                                jq '.campaigns[] | select(.name=="gcr-rs-dev-workshop-news-Sims-campaign")' | \
                                jq '.campaignArn' -r)
  if [[ "${sims_campaign_arn}" == "" ]]; then
    sims_campaign_arn=$($AWS_CMD personalize create-campaign --region $REGION \
            --name gcr-rs-${Stage}-news-Sims-campaign \
            --solution-version-arn ${sims_solution_version_arn} \
            --min-provisioned-tps 1 --output text)
  fi
else
  userPersonalize_campaign_arn=$($AWS_CMD personalize list-campaigns --region $REGION --solution-arn $userPersonalize_solution_arn | \
                                jq '.campaigns[] | select(.name=="gcr-rs-dev-workshop-news-UserPersonalize-campaign")' | \
                                jq '.campaignArn' -r)
  ranking_campaign_arn=$($AWS_CMD personalize list-campaigns --region $REGION --solution-arn $ranking_solution_arn | \
                                jq '.campaigns[] | select(.name=="gcr-rs-dev-workshop-news-Ranking-campaign")' | \
                                jq '.campaignArn' -r)
  sims_campaign_arn=$($AWS_CMD personalize list-campaigns --region $REGION --solution-arn $sims_solution_arn | \
                                jq '.campaigns[] | select(.name=="gcr-rs-dev-workshop-news-Sims-campaign")' | \
                                jq '.campaignArn' -r)
  if [[ "${userPersonalize_campaign_arn}" == "" ]]; then
    userPersonalize_campaign_arn=$($AWS_CMD personalize create-campaign --region $REGION \
            --name gcr-rs-${Stage}-news-UserPersonalize-campaign \
            --solution-version-arn ${userPersonalize_solution_version_arn} \
            --min-provisioned-tps 1 --output text)
  fi
  if [[ "${ranking_campaign_arn}" == "" ]]; then
    ranking_campaign_arn=$($AWS_CMD personalize create-campaign --region $REGION \
            --name gcr-rs-${Stage}-news-Ranking-campaign \
            --solution-version-arn ${ranking_solution_version_arn} \
            --min-provisioned-tps 1 --output text)
  fi
  if [[ "${sims_campaign_arn}" == "" ]]; then
    sims_campaign_arn=$($AWS_CMD personalize create-campaign --region $REGION \
            --name gcr-rs-${Stage}-news-Sims-campaign \
            --solution-version-arn ${sims_solution_version_arn} \
            --min-provisioned-tps 1 --output text)
  fi
fi


#monitor campaign
echo "Campaign Creating... It will takes no longer than 1 hours..."
MAX_TIME=`expr 1 \* 60 \* 60` # 1 hours
CURRENT_TIME=0
if [[ $METHOD == "ps-complete" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      userPersonalize_campaign_status=$($AWS_CMD personalize describe-campaign --region $REGION \
              --campaign-arn ${userPersonalize_campaign_arn} | jq '.campaign.status' -r)

      echo "userPersonalize_campaign_status: ${userPersonalize_campaign_status}"

      if [[ "$userPersonalize_campaign_status" = "CREATE FAILED" ]]
      then
          echo "!!!Campaign Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$userPersonalize_campaign_status" = "ACTIVE" ]]
      then
          echo "Campaign create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
elif [[ $METHOD == "ps-rank" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      ranking_campaign_status=$($AWS_CMD personalize describe-campaign --region $REGION \
              --campaign-arn ${ranking_campaign_arn} | jq '.campaign.status' -r)

      echo "ranking_campaign_status: ${ranking_campaign_status}"

      if [[ "$ranking_campaign_status" = "CREATE FAILED" ]]
      then
          echo "!!!Campaign Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$ranking_campaign_status" = "ACTIVE" ]]
      then
          echo "Campaign create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60

  done
elif [[ $METHOD == "ps-sims" ]]; then
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      sims_campaign_status=$($AWS_CMD personalize describe-campaign --region $REGION \
              --campaign-arn ${sims_campaign_arn} | jq '.campaign.status' -r)

      echo "sims_campaign_status: ${sims_campaign_status}"


      if [[ "$sims_campaign_status" = "CREATE FAILED" ]]
      then
          echo "!!!Campaign Create Failed!!!"
          echo "!!!Personalize Service Create Failed!!!"
          exit 8
      elif [[ "$sims_campaign_status" = "ACTIVE" ]]
      then
          echo "Campaign create successfully!"
          break;
      fi
      CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
      echo "wait for 1 min..."
      sleep 60
  done
else
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      userPersonalize_campaign_status=$($AWS_CMD personalize describe-campaign --region $REGION \
              --campaign-arn ${userPersonalize_campaign_arn} | jq '.campaign.status' -r)
      ranking_campaign_status=$($AWS_CMD personalize describe-campaign --region $REGION \
              --campaign-arn ${ranking_campaign_arn} | jq '.campaign.status' -r)
      sims_campaign_status=$($AWS_CMD personalize describe-campaign --region $REGION \
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
fi

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Creating Campaigns Time exceed 1 hour, please delete UserPersonalize Campaign and try again!"
    exit 8
fi

echo "Update ps_config.json ..."
config_file_path="./ps_config.json"
if [[ $REGION =~ cn.* ]];then
  sed -e "s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
              ./ps_config_template-cn.json > ${config_file_path}
else
  sed -e "s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
            ./ps_config_template.json > ${config_file_path}
fi

old_event_track_arn=$(awk -F"\"" '/EventTrackerArn/{print $4}' $config_file_path)
echo "change old_event_track_arn: ${old_event_track_arn} to new_event_track_arn: ${eventTrackerArn}"
sed -e "s@$old_event_track_arn@$eventTrackerArn@g" -i $config_file_path

old_event_track_id=$(awk -F"\"" '/EventTrackerId/{print $4}' $config_file_path)
echo "change old_event_track_id: ${old_event_track_id} to new_event_track_id: ${trackingId}"
sed -e "s@$old_event_track_id@$trackingId@g" -i $config_file_path

cp ./ps_config.json ../../sample-data/system/ps-config/ps_config.json
cp ./ps_config.json ../../sample-data/notification/ps-result/ps_config.json

rm -f ./ps_config.json

echo "Congratulations. Your AWS Personalize Service Create Successfully."

echo "Please stop printing the log by typing CONTROL+C "
