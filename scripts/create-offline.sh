#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

if [[ -z $REGION ]]; then
 export REGION='ap-northeast-1'
fi

echo "Stage=$Stage"
echo "REGION=$REGION"

if [[ -z $GITHUB_USER ]]; then
     echo "error!!! can not get your GITHUB_USER, please set it use 'export GITHUB_USER=<your github username>'"
     exit 1
fi
echo "GITHUB_USER: ${GITHUB_USER}"

sleep 3

echo "1. ========= sync sample data to S3 =============="
cd ${curr_dir}/../sample-data
./sync_data_to_s3.sh $Stage

echo "2. ========= Create codebuild =============="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline.sh $Stage

