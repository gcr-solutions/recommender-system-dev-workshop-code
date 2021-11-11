#!/usr/bin/env bash
set -e

echo "run $0 ..."
cur_dir=$(pwd)

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

METHOD=$2
if [[ -z $METHOD ]];then
  METHOD='customize'
fi

echo "METHOD=$METHOD"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -n $AWS_DEFAULT_REGION ]];then
  REGION=$AWS_DEFAULT_REGION
fi

if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

echo "AWS_CMD: $AWS_CMD"
echo "REGION: $REGION"


AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

method_list=(
    "customize"
    "ps-complete"
    "ps-rank"
    "ps-sims"
)
for method in ${method_list[@]};
do
  cd ${cur_dir}/${method}
  ./clean_up.sh
done

cd ${cur_dir}

