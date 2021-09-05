d#!/usr/bin/env bash
set -e

# export PROFILE=rsops
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

echo "AWS_CMD:$AWS_CMD"

if [[ -z $REGION ]];then
    REGION='ap-southeast-1'
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

news_projects=(
  "item-preprocessing"
  "add-item-batch"
  "item-feature-update-batch"
  "model-update-embedding"
  "prepare-training-data"
  "model-update-action"
  "dashboard"
  "action-preprocessing"
  "user-preprocessing"
  "add-user-batch"
  "portrait-batch"
  "load-portrait"
  "recall-batch"
  "rank-batch"
  "filter-batch"
  "assembled/data-preprocessing"
  "assembled/train-model"
  "inverted-list"
  "step-funcs"
)

for project in ${news_projects[@]}; do
  projectName=$(echo $project | sed "s#/#-#g")
  build_proj_name="rs-$Stage-offline-news-ps-sims-${projectName}-build"
  build_codebuild_project $build_proj_name
done

project="lambda"
build_proj_name="rs-$Stage-offline-${project}-build"
build_codebuild_project $build_proj_name









