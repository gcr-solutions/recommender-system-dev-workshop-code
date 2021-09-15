#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
fi

echo "Stage=$Stage"

repoName=rs/news-ps-rank-item-feature-update-batch

if [[ $Stage == 'demo' ]]; then
    ../dev2demo.sh $repoName
else
    rm -rf fasthan_base >/dev/null 2>&1
    mkdir fasthan_base
    if [[ $REGION =~ ^cn.* ]]; then
      cd ./fasthan_base
      wget https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/fasthan_base.zip
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

