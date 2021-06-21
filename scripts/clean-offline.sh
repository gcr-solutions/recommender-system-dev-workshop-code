#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

echo "==== Clean sample data in S3 ===="
cd ${curr_dir}/../sample-data/
./clean_up.sh

echo "==== DELETE all codebuild projects ===="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline.sh dev DELETE

echo "==== DELETE all Step funcs and ECR repos ===="
cd ${curr_dir}/../src/offline/
./clean_up.sh

echo "All offline resources were deleted"






