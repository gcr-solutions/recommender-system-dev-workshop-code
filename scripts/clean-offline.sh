#!/usr/bin/env bash
#set -e

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
     echo "error!!! can not get your GITHUB_USER, please set it use 'export GITHUB_USER=<your username>'"
     exit 1
fi

echo "GITHUB_USER: ${GITHUB_USER}"

sleep 3

echo "==== Clean sample data in S3 ===="
cd ${curr_dir}/../sample-data/
./clean_up.sh $Stage

echo "==== DELETE all codebuild projects ===="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline.sh $Stage DELETE

echo "==== DELETE all Step funcs and ECR repos ===="
cd ${curr_dir}/../src/offline/
./clean_up.sh $Stage

echo "All offline resources were deleted"






