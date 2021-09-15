#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
fi

echo "Stage=$Stage"
repoName=rs/news-ps-rank-portrait-batch

if [[ $Stage == 'demo' ]]; then
  ../dev2demo.sh $repoName
else
../norm_build.sh $repoName $Stage
fi
