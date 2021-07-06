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
echo "REGION: $REGION"

sleep 5

curr_dir=$(pwd)

cd ${curr_dir}/lambda/
./build.sh $Stage

cd ${curr_dir}/news/
./build.sh $Stage
