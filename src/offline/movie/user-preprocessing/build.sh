#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
fi

echo "Stage=$Stage"

repoName=rs/movie-user-preprocessing

if [[ $Stage == 'demo' ]]; then
  ../dev2demo.sh $repoName
else
../spark_build.sh $repoName $Stage
fi