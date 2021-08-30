#!/usr/bin/env bash

echo "run $0"

repoName=$1
tag=$2

if [[ -z $repoName ]];then
  echo "repoName is empty"
  exit 1
fi

if [[ -z $tag ]];then
  tag='latest'
fi

if [[ -z $CN_AWS_DEFAULT_REGION ]]; then
   CN_AWS_DEFAULT_REGION="cn-north-1"
fi

echo "repoName: $repoName, tag: $tag"

if [[ -z $CN_AWS_ACCESS_KEY_ID || -z $CN_AWS_SECRET_ACCESS_KEY || -z $CN_AWS_DEFAULT_REGION ]];then
    echo "CN_AWS_ACCESS_KEY_ID is empty, please set env: CN_AWS_ACCESS_KEY_ID|CN_AWS_SECRET_ACCESS_KEY|CN_AWS_DEFAULT_REGION "
    exit 1
fi

export AWS_ACCESS_KEY_ID=$CN_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$CN_AWS_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=$CN_AWS_DEFAULT_REGION

ACCOUNT_ID=$(aws  sts get-caller-identity --query Account --output text)

if [[ $? != 0 ]];then
     echo "Error"
     echo "ID/LEN: ${#CN_AWS_ACCESS_KEY_ID}/${#CN_AWS_SECRET_ACCESS_KEY}"
     exit 1
fi

echo "ACCOUNT_ID:$ACCOUNT_ID"

create_repo () {
  name=$1
  region=$2

  echo "create_repo() - name: $name, region: $region"

  aws  ecr create-repository  \
  --repository-name $name \
  --image-scanning-configuration scanOnPush=true \
  --region $region >/dev/null 2>&1 || true
}

aws  ecr get-login-password --region $CN_AWS_DEFAULT_REGION | \
docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$CN_AWS_DEFAULT_REGION.amazonaws.com.cn

create_repo $repoName $CN_AWS_DEFAULT_REGION

cn_account_ecr_uri=${ACCOUNT_ID}.dkr.ecr.${CN_AWS_DEFAULT_REGION}.amazonaws.com.cn

CN_IMAGE_URI=${cn_account_ecr_uri}/$repoName:$tag

docker tag $repoName:$tag ${CN_IMAGE_URI}

echo ">> push ${CN_IMAGE_URI}"
docker push ${CN_IMAGE_URI}
if [[ $? != 0 ]];then
     echo "Error docker push ${CN_IMAGE_URI}"
     exit 1
fi

echo "Done"






