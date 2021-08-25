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

if [[ -z $CN_AWS_ACCESS_KEY_ID ]];then
    echo "CN_AWS_ACCESS_KEY_ID is empty, please set env: CN_AWS_ACCESS_KEY_ID|CN_AWS_SECRET_ACCESS_KEY "
    exit 1
fi

mkdir ~/.aws/ > /dev/null 2>&1 || true

echo "[cn]" > ~/.aws/credentials_cn
echo "aws_access_key_id = $CN_AWS_ACCESS_KEY_ID"  >> ~/.aws/credentials_cn
echo "aws_secret_access_key = $CN_AWS_SECRET_ACCESS_KEY"  >> ~/.aws/credentials_cn

echo "[profile cn]" > ~/.aws/config_cn
echo "region = $CN_AWS_DEFAULT_REGION" >> ~/.aws/config_cn

export AWS_SHARED_CREDENTIALS_FILE=~/.aws/credentials_cn
export AWS_CONFIG_FILE=~/.aws/config_cn

ACCOUNT_ID=$(aws --profile cn sts get-caller-identity --query Account --output text)

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

  aws --profile cn ecr create-repository  \
  --repository-name $name \
  --image-scanning-configuration scanOnPush=true \
  --region $region >/dev/null 2>&1 || true
}

aws --profile cn ecr get-login-password --region $CN_AWS_DEFAULT_REGION | \
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






