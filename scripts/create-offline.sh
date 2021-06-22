#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

echo "1. ========= sync sample data to S3 =============="
cd ${curr_dir}/../sample-data
./sync_data_to_s3.sh

echo "2. ========= Create codebuild =============="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline.sh

