#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
fi

echo "Stage=$Stage"

curr_dir=$(pwd)

cd ${curr_dir}/data-preprocessing/
./build.sh $Stage
if [[ $? != 0 ]];then
     echo "Error"
     exit 1
fi

cd ${curr_dir}/train-model/
./build.sh $Stage
if [[ $? != 0 ]];then
     echo "Error"
     exit 1
fi