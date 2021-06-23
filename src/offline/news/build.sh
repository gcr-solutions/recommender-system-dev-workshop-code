#!/usr/bin/env bash
set -e

#export PROFILE='rsops'
#export REGION='ap-northeast-1'
#export REGION='ap-northeast-1'
#export PUBLIC_IMAGEURI=1

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

echo "AWS_CMD=$AWS_CMD"
echo "REGION=$REGION"
AWS_REGION=$REGION

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"


steps=(
item-preprocessing
add-item-batch
item-feature-update-batch
inverted-list
model-update-embedding
prepare-training-data
model-update-action
dashboard
action-preprocessing
user-preprocessing
add-user-batch
portrait-batch
recall-batch
rank-batch
filter-batch
)

total_size=${#steps[*]}
n=1

build_dir=$(pwd)
for t in ${steps[@]};
do
   cd ${build_dir}/${t}
   echo ">> ${n}/${total_size} [$Stage] Build ${t} ..."
    ./build.sh $Stage
    if [[ $? -ne 0 ]]; then
       echo "error!!!"
       exit 1
    fi
    sleep 5
    n=$(( n + 1 ))
done

echo "Done."


