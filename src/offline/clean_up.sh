#!/usr/bin/env bash
#set -e

#export PROFILE='rsops'
#export REGION='ap-northeast-1'

echo "run $0 ..."
pwd


echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi
AWS_REGION=$REGION

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

SCENARIO=$2
if [[ -z $SCENARIO  ]];then
    SCENARIO=news
fi

echo "SCENARIO: $SCENARIO"

curr_dir=$(pwd)

if [[ -n $RS_KEEP_OFFLINE_LAMBDA ]];then
   echo "skip delete lambda"
else
   cd ${curr_dir}/lambda/
   ./clean_up.sh $Stage
fi

cd ${curr_dir}/$SCENARIO/
./clean_up.sh $Stage
