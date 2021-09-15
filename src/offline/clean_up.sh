#!/usr/bin/env bash
#set -e

#export PROFILE='rsops'
#export REGION='ap-northeast-1'

echo "run $0 ..."
pwd


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
AWS_REGION=$REGION

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

curr_dir=$(pwd)

cd ${curr_dir}/lambda/
./clean_up.sh $Stage

cd ${curr_dir}

scenario_list=(
  news
)

method_list=(
  customize
  ps-complete
  ps-rank
  ps-sims
)

for scenario in ${scenario_list[@]};do
  for method in ${method_list[@]};do
    dir_path=${curr_dir}/${scenario}/${method}
    if [[ -d "${dir_path}" ]];then
      cd ${curr_dir}/${scenario}/${method}
      ./clean_up.sh $Stage
      cd ..
    fi
  done
done

