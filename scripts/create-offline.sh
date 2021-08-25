#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

echo "Stage=$Stage"
echo "REGION=$REGION"

if [[ -z $GITHUB_USER ]]; then
     echo "error!!! can not get your GITHUB_USER, please set it use 'export GITHUB_USER=<your github username>'"
     exit 1
fi
echo "GITHUB_USER: ${GITHUB_USER}"

AWS_CMD="aws"

if [[ -n $AWS_PROFILE ]]; then
  export PROFILE=$AWS_PROFILE
fi

if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
  DEPLOY_AWS_PROFILE=$PROFILE
fi

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

sleep 3

echo "1. ========= Create codebuild =============="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline.sh $Stage

if [[ $CN_AWS_PROFILE ]];then
  export PROFILE=$CN_AWS_PROFILE
  export CN_REGION='cn-north-1'
  export REGION=$CN_REGION

  AWS_CMD="aws --profile $PROFILE"
  AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${CN_REGION} --query Account --output text)

  echo "--------------$REGION-------------------------"
  echo "change PROFILE to $PROFILE"
  echo "change AWS_ACCOUNT_ID to $AWS_ACCOUNT_ID"
  echo "change REGION to $REGION"
  sleep 5
fi

echo "2. ========= sync sample data to S3 =============="
cd ${curr_dir}/../sample-data
./sync_data_to_s3.sh $Stage


echo "3. ========= Build lambda =============="
cd ${curr_dir}/../src/offline/lambda
./build.sh $Stage

echo "4. ========= Build stepfuncs =============="
cd ${curr_dir}/../src/offline/news/step-funcs
./build.sh $Stage

echo "Offline resources are created successfully"
echo "You can run your step-funcs with below input"

echo '{
  "Bucket": "aws-gcr-rs-sol-'${Stage}'-'${REGION}'-'${AWS_ACCOUNT_ID}'",
  "S3Prefix": "sample-data-news",
  "change_type": "ITEM|BATCH|USER|MODEL"
}'
echo ""

if [[ $CN_AWS_PROFILE ]];then
  export PROFILE=$DEPLOY_AWS_PROFILE
fi

