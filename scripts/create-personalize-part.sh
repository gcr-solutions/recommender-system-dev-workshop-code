#!/usr/bin/env bash
set -e

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

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "METHOD: ${METHOD}"
echo "Stage: ${Stage}"
echo "SCENARIO: ${SCENARIO}"
echo "REGION: ${REGION}"
echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"


echo "====================Create Personalize Service==============================="
cd ${curr_dir}/personalize
mkdir ~/personalize-log
nohup ./create-personalize.sh >> ~/personalize-log/create-personalize.log 2>&1 &
cd ${curr_dir}

echo "====================Create Personalize Offline Part==============================="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline-codecommit.sh $Stage "no" "personalize"
cd ${curr_dir}

