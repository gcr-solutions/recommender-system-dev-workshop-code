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
rs/news-customize-action-preprocessing
rs/news-customize-add-item-batch
rs/news-customize-add-user-batch
rs/news-customize-dashboard
rs/news-customize-filter-batch
rs/news-customize-inverted-list
rs/news-customize-item-feature-update-batch
rs/news-customize-item-preprocessing
rs/news-customize-model-update-action-gpu
rs/news-customize-model-update-embedding-gpu
rs/news-customize-portrait-batch
rs/news-customize-prepare-training-data
rs/news-customize-rank-batch
rs/news-customize-recall-batch
rs/news-customize-user-preprocessing
)

method_list=(
  "customize"
  "ps-complete"
  "ps-rank"
  "ps-sims"
)

curr_dir=$(pwd)

echo "1. Delete step-funcs"
cd $curr_dir/step-funcs
./clean_up.sh

cd $curr_dir

echo "2. Delete ECR repositories ..."
for method in ${method_list[@]}
do
  for repo in ${repo_names[@]}
  do
    repo_name=rs/news-${method}-${repo}
    if [[ "$AWS_ACCOUNT_ID" != '522244679887' ]]; then
         echo "Delete repo: '$repo_name ...'"
         $AWS_CMD ecr delete-repository  --repository-name $repo_name --region ${REGION} --force  > /dev/null 2>&1 || true
    else
        # our test  account: 522244679887
        echo "skip deleting repo: '$repo_name ...'"
    fi
  done
done
echo "Done"


