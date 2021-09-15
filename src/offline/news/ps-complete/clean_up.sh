#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
fi

echo "Stage=$Stage"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -z $REGION ]]; then
  REGION='ap-southeast-1'
fi

echo "AWS_CMD=$AWS_CMD"
echo "REGION=$REGION"
AWS_REGION=$REGION

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

repo_names=(
rs/news-ps-complete-action-preprocessing
rs/news-ps-complete-item-preprocessing
rs/news-ps-complete-user-preprocessing
rs/news-ps-complete-batch-preprocessing
)

curr_dir=$(pwd)

cd $curr_dir/step-funcs
./clean_up.sh

cd $curr_dir

for repo_name in ${repo_names[@]}
do
  echo "Delete repo: '$repo_name ...'"
  $AWS_CMD ecr delete-repository  --repository-name $repo_name --force > /dev/null 2>&1 || true
done

echo "Done"


