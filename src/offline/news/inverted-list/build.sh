#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

if [[ -n $REGION ]];then
  AWS_REGION=$REGION
fi

if [[ -z $AWS_REGION ]];then
  AWS_REGION='ap-northeast-1'
fi

echo "Stage=$Stage, AWS_REGION=$AWS_REGION"

repoName=rs/news-inverted-list
if [[ -n $REPO_NAME ]];then
  repoName=$REPO_NAME
fi


function download_dgl() {
    url=$1
    echo "download:$url"
    rm -rf ./dgl > /dev/null  2>&1
    mkdir ./dgl
    wget --quiet $url || {
        echo "error: fail to download $url"
        exit 1
    }
    unzip dgl-ke.zip
    rm dgl-ke.zip
    cd ..
}

dgl_url=https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/dgl/dgl-ke.zip

if [[ $Stage == 'demo' ]]; then
   ../dev2demo.sh $repoName
else
    rm -rf fasthan_base >/dev/null 2>&1
    mkdir fasthan_base
    if [[ $AWS_REGION =~ ^cn.* ]]; then
      dgl_url=https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/gcr-rs/dgl/dgl-ke.zip

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

    # install dgl-ke.zip
    download_dgl $dgl_url

    ../norm_build.sh $repoName $Stage

    rm -rf fasthan_base
    rm -rf ./dgl
fi
