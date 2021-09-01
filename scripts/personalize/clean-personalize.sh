#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

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

SCENARIO=$2

if [[ -z $SCENARIO ]];then
    SCENARIO='News'
fi

echo "Stage=$Stage"
echo "REGION=$REGION"
echo "SCENARIO=$SCENARIO"

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

dataset_group_arn="arn:aws:personalize:${REGION}:${AWS_ACCOUNT_ID}:dataset-group/GCR-RS-${SCENARIO}-Dataset-Group"
echo "dataset_group_arn:$dataset_group_arn"

echo "----------------------Clean Campaigns----------------------"
solution_arns=$(aws personalize list-solutions --dataset-group-arn ${dataset_group_arn} | jq '.[][]' | jq '.solutionArn' -r)
if [[ -n ${solution_arns} ]]; then
  for solution_arn in $(echo ${solution_arns}); do
    campaign_arns=$(aws personalize list-campaigns --solution-arn ${solution_arn} | jq '.[][]' | jq '.campaignArn' -r)
    if [ "${campaign_arns}" != "" ]; then
      for campaigns_arn in $(echo ${campaign_arns}); do
        aws personalize delete-campaign --campaign-arn ${campaigns_arn}
      done
    fi

    echo "Start deleting campaigns of ${solution_arn} ... It will takes no longer than 10 min..."
    MAX_TIME=`expr 10 \* 60` # 10 min
    CURRENT_TIME=0
    while(( ${CURRENT_TIME} < ${MAX_TIME} ))
    do
        campaign_list=$(aws personalize list-campaigns \
                    --solution-arn ${solution_arn} | jq '.campaigns' -r)

        if [[ $campaign_list == [] ]]
        then
            echo "Complete deleting campaigns of ${solution_arn}"
            break
        fi

        CURRENT_TIME=`expr ${CURRENT_TIME} + 30`
        echo "Delete Campaigns of ${solution_arn} In Progress, Wait For 30 Seconds..."
        sleep 30

    done

    if [ $CURRENT_TIME -ge $MAX_TIME ]
    then
        echo "The campaigns of ${solution_arn} has been deleted for more than 10 minutes, please delete manually!"
        exit 8
    fi
  done
fi


echo "----------------------Clean Solutions----------------------"
if [[ -n ${solution_arns} ]]; then
  for solution_arn in $(echo ${solution_arns}); do
    aws personalize delete-solution --solution-arn ${solution_arn}
  done

  echo "Solution Deleting... It will takes no longer than 10 min..."
  MAX_TIME=`expr 10 \* 60` # 10 min
  CURRENT_TIME=0
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      solution_list=$(aws personalize list-solutions \
                  --dataset-group-arn ${dataset_group_arn} | jq '.solutions' -r)

      if [[ $solution_list == [] ]]
      then
          echo "Complete deleting solutions"
          break
      fi

      CURRENT_TIME=`expr ${CURRENT_TIME} + 30`
      echo "Delete solutions In Progress, Wait For 30 Seconds..."
      sleep 30

  done

  if [ $CURRENT_TIME -ge $MAX_TIME ]
  then
      echo "The solutions have been deleted for more than 10 min, please delete manually!"
      exit 8
  fi
fi


echo "----------------------Clean EventTrackers----------------------"
event_tracker_arns=$(aws personalize list-event-trackers --dataset-group-arn ${dataset_group_arn} | jq '.[][]' | jq '.eventTrackerArn' -r)
if [[ -n ${event_tracker_arns} ]]; then
  for event_tracker_arn in $(echo ${event_tracker_arns}); do
    aws personalize delete-event-tracker --event-tracker-arn ${event_tracker_arn}
  done

  echo "EventTracker Deleting... It will takes no longer than 10 min..."
  MAX_TIME=`expr 10 \* 60` # 10 min
  CURRENT_TIME=0
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      event_tracker_list=$(aws personalize list-event-trackers \
                  --dataset-group-arn ${dataset_group_arn} | jq '.eventTrackers' -r)

      if [[ $event_tracker_list == [] ]]
      then
          echo "Complete deleting EventTracker"
          break
      fi

      CURRENT_TIME=`expr ${CURRENT_TIME} + 30`
      echo "Delete EventTracker In Progress, Wait For 30 Seconds..."
      sleep 30

  done

  if [ $CURRENT_TIME -ge $MAX_TIME ]
  then
      echo "The EventTracker has been deleted for more than 10 min, please delete manually!"
      exit 8
  fi
fi


echo "----------------------Clean Datasets----------------------"
dataset_arns=$(aws personalize list-datasets --dataset-group-arn ${dataset_group_arn} | jq '.[][]' | jq '.datasetArn' -r)
if [[ -n ${dataset_arns} ]]; then
  for dataset_arn in $(echo ${dataset_arns}); do
    aws personalize delete-dataset --dataset-arn ${dataset_arn}
  done

  echo "Datasets Deleting... It will takes no longer than 20 min..."
  MAX_TIME=`expr 20 \* 60` # 10 min
  CURRENT_TIME=0
  while(( ${CURRENT_TIME} < ${MAX_TIME} ))
  do
      dataset_list=$(aws personalize list-datasets \
                  --dataset-group-arn ${dataset_group_arn} | jq '.datasets' -r)

      if [[ $dataset_list == [] ]]
      then
          echo "Complete deleting datasets"
          break
      fi

      CURRENT_TIME=`expr ${CURRENT_TIME} + 30`
      echo "Delete datasets In Progress, Wait For 30 Seconds..."
      sleep 30

  done

  if [ $CURRENT_TIME -ge $MAX_TIME ]
  then
      echo "The Datasets have been deleted for more than 20 min, please delete manually!"
      exit 8
  fi
fi


echo "----------------------Clean Schemas----------------------"
aws personalize delete-schema --schema-arn "arn:aws:personalize:${REGION}:${AWS_ACCOUNT_ID}:schema/${SCENARIO}UserSchema" > /dev/null 2>&1 || true
aws personalize delete-schema --schema-arn "arn:aws:personalize:${REGION}:${AWS_ACCOUNT_ID}:schema/${SCENARIO}ItemSchema" > /dev/null 2>&1 || true
aws personalize delete-schema --schema-arn "arn:aws:personalize:${REGION}:${AWS_ACCOUNT_ID}:schema/${SCENARIO}InteractionSchema" > /dev/null 2>&1 || true


echo "----------------------Clean DatasetGroup----------------------"
aws personalize delete-dataset-group --dataset-group-arn ${dataset_group_arn} > /dev/null 2>&1 || true

#delete codebuild role and policy
echo "----------------------Clean Personalize Policy and Role----------------------"
ROLE_NAME=gcr-rs-personalize-role
ROLE_POLICY=gcr-rs-personalize-policy
echo "Role Name=${ROLE_NAME}"
echo "Policy Name=${ROLE_POLICY}"

ROLE_NAMES=$(aws iam list-roles | jq '.[][] | select(.RoleName=="gcr-rs-personalize-role")')
if [ "$ROLE_NAMES" == "" ]
then
    echo "Nothing has been done and all clear."
else
    aws iam list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'
    for policyArn in `aws iam list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'`
    do
        aws iam detach-role-policy \
            --role-name ${ROLE_NAME} \
            --policy-arn ${policyArn}
        echo "Detached ${ROLE_NAME} and ${policyArn}"

        count=`aws iam list-policy-versions --policy-arn ${policyArn} |jq -r '.Versions[].VersionId'|wc -l`
        if [ $count -eq '1' ]
        then
            aws iam delete-policy --policy-arn ${policyArn} || true
        else
            for versionId in `aws iam list-policy-versions --policy-arn ${policyArn} |jq -r '.Versions[].VersionId'`
            do
                aws iam delete-policy-version \
                    --policy-arn ${policyArn} \
                    --version-id ${versionId}
                echo "Deleted ${ROLE_POLICY} = ${policyArn} : ${versionId}" || true
            done
            aws iam delete-policy --policy-arn ${policyArn}
        fi
    done
    aws iam delete-role --role-name ${ROLE_NAME}
    echo "Deleted ${ROLE_NAME}"
fi
echo "Clean Personalize Policy and Role Successfully!"