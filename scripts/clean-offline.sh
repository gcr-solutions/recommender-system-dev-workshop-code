#!/usr/bin/env bash
#set -e

curr_dir=$(pwd)

Stage=$1
if [[ -z $Stage ]]; then
  Stage='dev-workshop'
fi

if [[ -z $REGION ]]; then
  export REGION='ap-northeast-1'
fi

#if [[ -n $AWS_PROFILE ]]; then
#  export PROFILE=$AWS_PROFILE
#fi

AWS_CMD='aws'

if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

echo "Stage=$Stage"
echo "REGION=$REGION"
echo "AWS_CMD=$AWS_CMD"

sleep 3

echo "==== DELETE all codebuild projects ===="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline.sh $Stage DELETE

repo_names=(
  rs/news-inverted-list
  rs/news-action-preprocessing
  rs/news-add-item-batch
  rs/news-add-user-batch
  rs/news-dashboard
  rs/news-filter-batch
  rs/news-item-feature-update-batch
  rs/news-item-preprocessing
  rs/news-model-update-action
  rs/news-model-update-embedding
  rs/news-portrait-batch
  rs/news-prepare-training-data
  rs/news-rank-batch
  rs/news-recall-batch
  rs/news-user-preprocessing
)

echo "Delete ECR repositories ..."
for repo_name in ${repo_names[@]}; do
  if [[ "$AWS_ACCOUNT_ID" != '522244679887' ]]; then
    echo "Delete repo: '$repo_name ...'"
    $AWS_CMD ecr delete-repository --repository-name $repo_name --region ${REGION} --force >/dev/null 2>&1 || true
  else
    # our test  account: 522244679887
    echo "skip deleting repo: '$repo_name ...'"
  fi
done


echo "==== Clean sample data in S3 ===="
cd ${curr_dir}/../sample-data/
./clean_up.sh $Stage

echo "==== DELETE all Step funcs and ECR repos ===="
cd ${curr_dir}/../src/offline/
./clean_up.sh $Stage

echo "All offline resources were deleted"

