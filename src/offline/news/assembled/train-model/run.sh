#!/usr/bin/env bash

echo "----------run.sh---------------------"

bucket=$1
prefix=$2

echo "bucket: $bucket"
echo "prefix: $prefix"
work_dir=$(pwd)

echo "work_dir: ${work_dir}"

echo "1. Start run add-item-user-batch.py..."
cd ./add-item-user-batch/
python3 add-item-user-batch.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step1"
     exit 1
fi
cd ${work_dir}

echo "2. Start run item-feature-update-batch.py..."
cd ./item-feature-update-batch/src/
python3 ./item-feature-update-batch.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step2"
     exit 1
fi
cd ${work_dir}

echo "3. Start run item-feature-update-batch.py..."
cd ./inverted-list/src/
python3 ./inverted-list.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step3"
     exit 1
fi

cd ${work_dir}

echo "4. Start run ./model-update-embedding/src/train.py..."
cd ./model-update-embedding/src/
python3 ./train.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step4"
     exit 1
fi

cd ${work_dir}

echo "5. Start run ./model-update-action/src/train.py..."
cd ./model-update-action/src/
echo "-------"
pwd
ls -l
echo "-------"

python3 ./train.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step5"
     exit 1
fi

cd ${work_dir}

echo "---------complete run.sh-------------------"