#!/usr/bin/env bash
set -e

echo "update ps_config.json ...."
curr_dir=$(pwd)

METHOD=$1

if [[ -z $METHOD ]];then
  METHOD='customize'
fi

Stage=$2

if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

SCENARIO=$3

if [[ -z $SCENARIO ]];then
  SCENARIO='news'
fi

if [[ -z $REGION ]];then
  REGION='ap-southeast-1'
fi

profile=aws
if [[ $REGION =~ cn.* ]];then
  profile=aws-cn
fi

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi


BUCKET_BUILD=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=sample-data-${SCENARIO}


if [ $METHOD = "ps-complete" ]
then
    solution_name="UserPersonalizeSolution"
    campaign_name="gcr-rs-${Stage}-${SCENARIO}-UserPersonalize-campaign"
    campaign_arn="arn:${profile}:personalize:${REGION}:${AWS_ACCOUNT_ID}:campaign/${campaign_name}"
    solution_version_arn=$(aws personalize describe-campaign --campaign-arn ${campaign_arn} | jq '.campaign.solutionVersionArn' -r)
elif [ $METHOD = "ps-rank" ]
then
    solution_name="RankingSolution"
    campaign_name="gcr-rs-${Stage}-${SCENARIO}-Ranking-campaign"
    campaign_arn="arn:${profile}:personalize:${REGION}:${AWS_ACCOUNT_ID}:campaign/${campaign_name}"
    solution_version_arn=$(aws personalize describe-campaign --campaign-arn ${campaign_arn} | jq '.campaign.solutionVersionArn' -r)
elif [ $METHOD = "ps-sims" ]
then
    solution_name="SimsSolution"
    campaign_name="gcr-rs-${Stage}-${SCENARIO}-Sims-campaign"
    campaign_arn="arn:${profile}:personalize:${REGION}:${AWS_ACCOUNT_ID}:campaign/${campaign_name}"
    solution_version_arn=$(aws personalize describe-campaign --campaign-arn ${campaign_arn} | jq '.campaign.solutionVersionArn' -r)
fi

config_file_path=${curr_dir}/../../sample-data/system/ps-config/ps_config.json

if [ $METHOD != "customize" ]
then
  echo "------update ps_config.json file-------"
  old_solution_name=$(awk -F"\"" '/SolutionName/{print $4}' $config_file_path)
  echo "change old_solution_name: ${old_solution_name} to new_solution_name: ${solution_name}"
  sed -e "s@$old_solution_name@$solution_name@g" -i  $config_file_path > /dev/null

  old_solution_version_arn=$(awk -F"\"" '/SolutionVersionArn/{print $4}' $config_file_path)
  echo "change old_solution_version_arn: ${old_solution_version_arn} to new_solution_version_arn: ${solution_version_arn}"
  sed -e "s@$old_solution_version_arn@$solution_version_arn@g" -i $config_file_path > /dev/null

  old_campaign_name=$(awk -F"\"" '/CampaignName/{print $4}' $config_file_path)
  echo "change old_campaign_name: ${old_campaign_name} to new_campaign_name: ${campaign_name}"
  sed -e "s@$old_campaign_name@$campaign_name@g" -i $config_file_path > /dev/null

  old_campaign_arn=$(awk -F"\"" '/CampaignArn/{print $4}' $config_file_path)
  echo "change old_campaign_arn: ${old_campaign_arn} to new_campaign_arn: ${campaign_arn}"
  sed -e "s@$old_campaign_arn@$campaign_arn@g" -i $config_file_path > /dev/null

fi
