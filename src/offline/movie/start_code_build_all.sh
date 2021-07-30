#!/usr/bin/env bash
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

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

build_codebuild_project () {
  build_proj_name=$1
  echo "Start build: ${build_proj_name}"
  $AWS_CMD codebuild start-build  --project-name ${build_proj_name} > /dev/null
  if [[ $? != 0 ]];then
     echo "Error run aws codebuild start-build"
     exit 1
  fi

}

movie_projects=(
  "action-preprocessing"
  "dashboard"
  "item-preprocessing"
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
  "user-preprocessing"
  "step-funcs"
)

for project in ${movie_projects[@]}; do
  build_proj_name="rs-$Stage-offline-movie-${project}-build"
  build_codebuild_project $build_proj_name
done

project="lambda"
build_proj_name="rs-$Stage-offline-${project}-build"
build_codebuild_project $build_proj_name









