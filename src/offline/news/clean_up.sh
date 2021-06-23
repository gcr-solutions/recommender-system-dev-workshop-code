#!/usr/bin/env bash
#set -e

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

repo_names=(
rs/news-action-preprocessing
rs/news-add-item-batch
rs/news-add-user-batch
rs/news-dashboard
rs/news-filter-batch
rs/news-inverted-list
rs/news-item-feature-update-batch
rs/news-item-preprocessing
rs/news-model-update-action-gpu
rs/news-model-update-embedding-gpu
rs/news-portrait-batch
rs/news-prepare-training-data
rs/news-rank-batch
rs/news-recall-batch
rs/news-user-preprocessing
#rs/news-weight-update-batch
)

curr_dir=$(pwd)

echo "1. Delete step-funcs"
cd $curr_dir/step-funcs
./clean_up.sh

cd $curr_dir

echo "2. Delete ECR repositories ..."
for repo_name in ${repo_names[@]}
do
  if [[ "$AWS_ACCOUNT_ID" != '522244679887' ]]; then
       echo "Delete repo: '$repo_name ...'"
       $AWS_CMD ecr delete-repository  --repository-name $repo_name --region ${REGION} --force || true
  else
      # our test  account: 522244679887
      echo "skip deleting repo: '$repo_name ...'"
  fi
done

echo "Done"


