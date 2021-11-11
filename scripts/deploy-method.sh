#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

METHOD=$1

if [[ -z $METHOD ]];then
  METHOD='customize'
fi

if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

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

if [[ "$METHOD" == "ps-complete" || "$METHOD" == "ps-rank" || "$METHOD" == "ps-sims" ]]; then
  echo "====================Create Personalize Service==============================="
  cd ${curr_dir}/personalize
  ./create-personalize.sh $METHOD $Stage
  cd ${curr_dir}
fi

echo "====================Create ${METHOD} Offline Part==============================="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline-codecommit.sh $Stage "no" ${METHOD} ${SCENARIO}
cd ${curr_dir}

echo "====================Switch to ${METHOD} Method=========================="
./setup-rs-system.sh change-method ${METHOD}

echo "Please stop printing the log by typing CONTROL+C "

