#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

if [[ -n $REGION ]];then
  AWS_REGION=$REGION
fi

echo "Stage=$Stage, AWS_REGION=$AWS_REGION"

repoName=rs/news-model-update-embedding
if [[ -n $REPO_NAME ]];then
  repoName=$REPO_NAME
fi

if [[ $Stage == 'demo' ]]; then
    ../dev2demo.sh $repoName
else
    rm -rf fasthan_base >/dev/null 2>&1
    mkdir fasthan_base
    if [[ $AWS_REGION =~ ^cn.* ]]; then
      cd ./fasthan_base
      wget --quiet https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/gcr-rs/fasthan/fasthan_base.zip || {
        echo "error: fail to download fasthan_base.zip"
        exit 1
      }
    else
      aws s3 cp s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/fasthan_base.zip ./fasthan_base
      cd fasthan_base
    fi
    unzip fasthan_base.zip
    rm fasthan_base.zip
    cd ..

    ../norm_build.sh $repoName $Stage

    rm -r fasthan_base
fi
