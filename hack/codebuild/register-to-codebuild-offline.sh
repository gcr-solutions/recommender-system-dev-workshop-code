#!/bin/bash

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

roleArn=$(cat role.arn)
if [[ $? -ne 0 ]]; then
  #echo "ERROR: cannot read file role.arn, please set your codebuild role in file: 'role.arn' or run ./create-iam-role.sh firstly"
  roleArn='arn:aws:iam::522244679887:role/rs-codebuild-role'
  #exit 1
fi


create_codebuild_project () {
  build_proj_name=$1
  app_path=$2
  echo "========== $build_proj_name ==============="
  echo "app_path:$app_path"
  echo "Deleting $build_proj_name from CodeBuild ..."
  $AWS_CMD codebuild  delete-project --name $build_proj_name || true
  echo "Done."
  sleep 5

  echo "Re-creating $build_proj_name into CodeBuild ..."
  sed -e 's/__app_name__/'${build_proj_name}'/g' ./codebuild-template-offline.json >./tmp-codebuild.json
  sed -e 's#__app_path__#'${app_path}'#g' ./tmp-codebuild.json > tmp-codebuild_2.json
  sed -e 's#__Stage__#'${Stage}'#g' ./tmp-codebuild_2.json > ./codebuild.json
  echo "------------------------------------"
  cat codebuild.json
  echo "------------------------------------"

  $AWS_CMD codebuild create-project \
    --cli-input-json file://codebuild.json \
    --service-role ${roleArn} > /dev/null

  if [[ $? != 0 ]];then
     echo "Error run aws codebuild create-project"
     exit 1
  fi

  sleep 2

  rm -f codebuild.json
  rm -f tmp-codebuild*.json

  echo "Start build: ${build_proj_name}"
  $AWS_CMD codebuild start-build  --project-name ${build_proj_name} > /dev/null
  if [[ $? != 0 ]];then
     echo "Error run aws codebuild start-build"
     exit 1
  fi

}

echo "----------------projects-------------------------"

projects_dir=(
  "lambda"
  "news/action-preprocessing"
  "news/user-preprocessing"
  "news/add-item-user-batch"
  "news/dashboard"
  "news/filter-batch"
  "news/inverted-list"
  "news/item-feature-update-batch"
  "news/item-preprocessing"
  "news/model-update-action"
  "news/model-update-embedding"
  "news/portrait-batch"
  "news/rank-batch"
  "news/recall-batch"
  "news/weight-update-batch"
  "news/assembled/data-preprocessing"
  "news/assembled/train-model"
  "news/step-funcs"
  "news"
  "movie/action-preprocessing"
  "movie/dashboard"
  "movie/item-preprocessing"
  "movie/filter-batch"
  "movie/inverted-list"
  "movie/rank-batch"
  "movie/recall-batch"
  "movie/model-update-deepfm"
  "movie/model-update-ub"
  "movie/portrait-batch"
  "movie/item-feature-update-batch"
  "movie/add-item-user-batch"
  "movie/weight-update-batch"
  "movie/step-funcs"
  "movie"
)

for project in ${projects_dir[@]}; do
  build_name=$(echo ${project} | sed 's#/#-#g')
  build_proj_name="rs-$Stage-offline-${build_name}-build"
  app_path=${project}
  create_codebuild_project $build_proj_name $app_path
done





