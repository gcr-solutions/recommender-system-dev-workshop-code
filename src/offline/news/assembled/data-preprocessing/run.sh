#!/usr/bin/env bash
set -e

echo "----------run.sh---------------------"

bucket=$1
prefix=$2

echo "bucket: $bucket"
echo "prefix: $prefix"
work_dir=$(pwd)

echo "work_dir: $work_dir"

echo "1. Start run item-preprocessing..."
cd ${work_dir}/item-preprocessing
python3 ./process.py --bucket $bucket --prefix $prefix

if [[ $? != 0 ]];then
     echo "Error step1 item-preprocessing"
     exit 1
fi

echo "2. Start run add-item-batch..."
cd ${work_dir}/add-item-batch
python3 ./add-item-batch.py --bucket $bucket --prefix $prefix

if [[ $? != 0 ]];then
     echo "Error step2 add-item-batch.py"
     exit 1
fi


echo "3. Start run action-preprocessing (only4popularity=1)..."
cd ${work_dir}/action-preprocessing
python3 ./process.py --bucket $bucket --prefix $prefix --only4popularity 1

if [[ $? != 0 ]];then
     echo "Error step3 action-preprocessing(only4popularity=1)"
     exit 1
fi


