echo "----------run.sh---------------------"

bucket=$1
prefix=$2

echo "bucket: $bucket"
echo "prefix: $prefix"
work_dir=$(pwd)

echo "work_dir: $work_dir"

echo "1. Start run user-preprocessing..."
cd ${work_dir}/user-preprocessing
python3 ./process.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step1 user-preprocessing"
     exit 1
fi

echo "2. Start run item-preprocessing..."
cd ${work_dir}/item-preprocessing
python3 ./process.py --bucket $bucket --prefix $prefix

if [[ $? != 0 ]];then
     echo "Error step2 item-preprocessing"
     exit 1
fi

echo "3. Start run add-item-user-batch.py..."
cd ${work_dir}/add-item-user-batch
python3 ./add-item-user-batch.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step3 add-item-user-batch.py"
     exit 1
fi


echo "4. Start run action-preprocessing..."
cd ${work_dir}/action-preprocessing
python3 ./process.py --bucket $bucket --prefix $prefix
if [[ $? != 0 ]];then
     echo "Error step4 action-preprocessing"
     exit 1
fi
