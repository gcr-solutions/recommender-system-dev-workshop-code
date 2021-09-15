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

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"

sleep 3

echo "==== DELETE all codebuild projects ===="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline-codecommit.sh $Stage DELETE

repo_names=(
  inverted-list
  action-preprocessing
  add-item-batch
  add-user-batch
  dashboard
  filter-batch
  item-feature-update-batch
  item-preprocessing
  model-update-action
  model-update-embedding
  portrait-batch
  prepare-training-data
  rank-batch
  recall-batch
  user-preprocessing
)

scenario_list=(
  news
)

method_list=(
  customize
  ps-complete
  ps-rank
  ps-sims
)

echo "Delete ECR repositories ..."

for scenario in ${scenario_list[@]}; do
  for method in ${method_list[@]}; do
    for repo_name in ${repo_names[@]}; do
      if [[ "$AWS_ACCOUNT_ID" != '522244679887' ]]; then
        echo "Delete repo: 'rs/$scenario-$method-$repo_name ...'"
        $AWS_CMD ecr delete-repository --repository-name rs/$scenario-$method-$repo_name --region ${REGION} --force >/dev/null 2>&1 || true
      else
        # our test  account: 522244679887
        echo "skip deleting repo: '$repo_name ...'"
      fi
    done
  done
done


echo "==== Clean sample data in S3 ===="
cd ${curr_dir}/../sample-data/
./clean_up.sh $Stage

echo "==== DELETE all Step funcs and ECR repos ===="
cd ${curr_dir}/../src/offline/
./clean_up.sh $Stage


#echo "==== DELETE Codebuild Role ===="
#cd ${curr_dir}/codebuild/
#./create-codebuild-role.sh $Stage 'DELETE'

echo "All offline resources were deleted"

echo "Please stop printing the log by typing CONTROL+C "
