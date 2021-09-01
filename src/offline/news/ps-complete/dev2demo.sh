#!/usr/bin/env bash
set -e

repoName=$1

if [[ -z ${repoName} ]];then
  echo "error repoName is empty"
  echo "Usage: $0 <repoName>"
  exit 1
fi

echo "[Dev to Demo] repoName: $repoName"



AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -n $AWS_DEFAULT_REGION ]];then
  REGION=$AWS_DEFAULT_REGION
fi

if [[ -z $REGION ]]; then
  REGION='ap-southeast-1'
fi

echo "AWS_CMD:'$AWS_CMD'"
echo "REGION: '$REGION'"

AWS_REGION=$REGION

account_id=$($AWS_CMD sts get-caller-identity --query Account --output text)

if [[ $AWS_REGION =~ ^cn.* ]]; then
  account_ecr_uri=${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com.cn
else
  account_ecr_uri=${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com
fi

IMAGEURI=${account_ecr_uri}/$repoName:dev

DEMO_IMAGEURI=${account_ecr_uri}/$repoName:demo

$AWS_CMD ecr get-login-password  --region ${AWS_REGION} | docker login --username AWS --password-stdin ${account_ecr_uri}

echo "pull ${IMAGEURI} ..."
docker pull ${IMAGEURI}
if [[ $? != 0 ]]; then
    echo "Error docker pull ${IMAGEURI}"
    exit 1
fi

docker tag ${IMAGEURI}  ${DEMO_IMAGEURI}

echo "push >> ${DEMO_IMAGEURI}"

docker push ${DEMO_IMAGEURI}

echo "Done"



