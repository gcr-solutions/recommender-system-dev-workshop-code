#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

echo "==== DELETE all codebuild projects ===="
cd ./codebuild
./register-to-codebuild-offline.sh dev DELETE

echo "==== DELETE all Step funcs and ECR repos ===="
cd $curr_dir/../src/offline/
./clean_up.sh

echo "All offline resources were deleted"






