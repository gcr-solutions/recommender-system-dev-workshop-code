#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
pwd

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -n $AWS_DEFAULT_REGION ]];then
  REGION=$AWS_DEFAULT_REGION
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

echo "AWS_CMD: $AWS_CMD"
echo "REGION: $REGION"
AWS_REGION=$REGION


AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

./package_code_to_s3.sh $Stage
if [[ $? -ne 0 ]]; then
    echo "error!!!"
    exit 1
fi
./deploy_lambda.sh $Stage
if [[ $? -ne 0 ]]; then
    echo "error!!!"
    exit 1
fi
./update_lambda_code.sh $Stage
if [[ $? -ne 0 ]]; then
    echo "error!!!"
    exit 1
fi

rm -rf deploy > /dev/null 2>&1
