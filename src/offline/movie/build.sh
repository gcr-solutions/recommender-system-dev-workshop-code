#!/usr/bin/env bash
set -e


# export PROFILE=rsops

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

AWS_REGION=$REGION

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

projects=(
  "action-preprocessing"
  "item-preprocessing"
  "user-preprocessing"
  "dashboard"
  "filter-batch"
  "inverted-list"
  "rank-batch"
  "recall-batch"
  "model-update-deepfm"
  "model-update-ub"
  "portrait-batch"
  "item-feature-update-batch"
  "add-item-batch"
  "add-user-batch"
  "step-funcs"
)

for project in ${projects[@]}; do
  echo "[$Stage] Start build: ${project}"
  cd $project
  ./build.sh $Stage
  if [[ $? -ne 0 ]]; then
    echo "error!!!"
    exit 1
  fi
  cd ..
done

echo "Done."
