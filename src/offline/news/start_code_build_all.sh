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

echo "AWS_CMD:$AWS_CMD"

if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

echo "PROFILE: $PROFILE"
echo "REGION: $REGION"
AWS_REGION=$REGION

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

build_codebuild_project () {
  build_proj_name=$1
  echo "Start build: ${build_proj_name}"
  $AWS_CMD codebuild  start-build  --project-name ${build_proj_name} > /dev/null
  if [[ $? != 0 ]];then
     echo "Error run aws codebuild start-build"
     exit 1
  fi

}

projects_dir=(
#  "lambda"
#  "news/step-funcs"
  "news/customize/item-preprocessing"
  "news/customize/add-item-batch"
  "news/customize/item-feature-update-batch"
  "news/customize/model-update-embedding"
  "news/customize/prepare-training-data"
  "news/customize/model-update-action"
  "news/customize/dashboard"
  "news/customize/action-preprocessing"
  "news/customize/user-preprocessing"
  "news/customize/add-user-batch"
  "news/customize/portrait-batch"
  "news/customize/recall-batch"
  "news/customize/rank-batch"
  "news/customize/filter-batch"
  "news/customize/inverted-list"
)

for project in ${projects_dir[@]}; do
  build_name=$(echo ${project} | sed 's#/#-#g')
  build_proj_name="rs-$Stage-offline-${build_name}-build"
  app_path=${project}
  build_codebuild_project $build_proj_name
done









