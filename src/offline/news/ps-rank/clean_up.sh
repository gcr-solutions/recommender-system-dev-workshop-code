#!/usr/bin/env bash
set -e

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
rs/news-ps-rank-action-preprocessing
rs/news-ps-rank-add-item-batch
rs/news-ps-rank-add-user-batch
rs/news-ps-rank-dashboard
rs/news-ps-rank-filter-batch
rs/news-ps-rank-inverted-list
rs/news-ps-rank-item-feature-update-batch
rs/news-ps-rank-item-preprocessing
rs/news-ps-rank-model-update-action-gpu
rs/news-ps-rank-model-update-embedding-gpu
rs/news-ps-rank-portrait-batch
rs/news-ps-rank-prepare-training-data
rs/news-ps-rank-rank-batch
rs/news-ps-rank-recall-batch
rs/news-ps-rank-user-preprocessing
#rs/news-weight-update-batch
)

curr_dir=$(pwd)

cd $curr_dir/step-funcs
./clean_up.sh

cd $curr_dir

for repo_name in ${repo_names[@]}
do
  echo "Delete repo: '$repo_name ...'"
  $AWS_CMD ecr delete-repository  --repository-name $repo_name --force || true
done

echo "Done"


