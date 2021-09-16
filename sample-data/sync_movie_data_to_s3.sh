#!/usr/bin/env bash

echo "################"

echo "run $0 ..."
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


if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

echo "REGION: $REGION"

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity  --o text | awk '{print $1}')
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET_BUILD=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=sample-data-movie

echo "BUCKET_BUILD=${BUCKET_BUILD}"
echo "Create S3 Bucket: ${BUCKET_BUILD} if not exist"


echo "########################################################"
echo "aws  s3 sync . s3://${BUCKET_BUILD}/${PREFIX}/"
echo "########################################################"

dataUrl=https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/data/sample-data-movie.zip

if [[ $REGION =~ cn.* ]];then
  dataUrl=https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/data/sample-data-movie.zip
fi

rm -rf movie-data >/dev/null 2>&1
mkdir movie-data && cd movie-data
echo "wget $dataUrl ..."
wget --quiet $dataUrl

if [[ $? -ne 0 ]];then
   echo  "error!!! wget $dataUrl"
   exit 1
fi

unzip sample-data-movie.zip > /dev/null
rm sample-data-movie.zip  sync_data_to_s3.sh

echo "$AWS_CMD  s3 sync . s3://${BUCKET_BUILD}/${PREFIX}/ ..."
$AWS_CMD  s3 sync . s3://${BUCKET_BUILD}/${PREFIX}/ > /dev/null

if [[ $? -ne 0 ]];then
   echo  "error!!! s3 sync"
   exit 1
fi

cd ..
rm -rf movie-data
echo "data sync completed"
