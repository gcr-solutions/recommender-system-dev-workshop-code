#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

echo "1. DELETE all codebuild projects"
cd ./codebuild
./register-to-codebuild-offline.sh dev DELETE

echo "2. DELETE all ECR repos"
cd $curr_dir/../src/offline/
./clean_up.sh

echo "All offline resources were deleted"






