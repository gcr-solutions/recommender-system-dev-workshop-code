#!/usr/bin/env bash
set -e

echo "----------run.sh---------------------"

bucket=$1
prefix=$2

echo "bucket: $bucket"
echo "prefix: $prefix"
work_dir=$(pwd)

echo "work_dir: ${work_dir}"

echo "1. Start run item-feature-update-batch.py..."
cd ${work_dir}/item-feature-update-batch/src
python3 ./item-feature-update-batch.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step1 item-feature-update-batch.py"
     exit 1
fi

#echo "2. Start run inverted-list.py..."
#cd ${work_dir}/inverted-list/src
#python3 ./inverted-list.py --bucket $bucket --prefix $prefix
#if [[ $? != 0 ]];then
#     echo "Error step2 inverted-list.py"
#     exit 1
#fi

echo "2. Start run ./model-update-embedding/src/train.py..."
cd ${work_dir}/model-update-embedding/src/
python3 ./train.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step3 model-update-embedding/src/train.py"
     exit 1
fi

cd ${work_dir}

echo "---------complete run.sh-------------------"