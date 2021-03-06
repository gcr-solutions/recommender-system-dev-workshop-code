#!/usr/bin/env bash
#set -e
# export PROFILE=rsops

cur_dir=$(pwd)

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

DELETE_FLAG=$2
if [[ -z $DELETE_FLAG ]];then
  DELETE_FLAG='no'
fi

METHOD=$3
if [[ -z $METHOD ]];then
  METHOD="customize"
fi

SCENARIO=$4

if [[ -z $SCENARIO ]];then
  SCENARIO="news"
fi

echo "Scenario: $SCENARIO"
echo "Method: $METHOD"
echo "Stage:$Stage"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

echo "AWS_CMD:$AWS_CMD"

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi
echo "REGION:$REGION"

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
AWS_P='aws'
if [[ $REGION =~ cn.* ]];then
  AWS_P='aws-cn'
fi

roleArn=$(cat _role.arn) ||  roleArn=''
if [[ -z $roleArn ]]; then
  roleArn="arn:${AWS_P}:iam::${AWS_ACCOUNT_ID}:role/gcr-rs-${Stage}-codebuild-role-${REGION}"
fi

echo "roleArn: $roleArn"
echo "DELETE_FLAG: $DELETE_FLAG"
echo ""

sleep 5

delete_codebuild_project () {
  build_proj_name=$1
  app_path=$2
  echo "========== $build_proj_name ==============="
  echo "app_path:$app_path"
  echo "Deleting $build_proj_name from CodeBuild ..."
  $AWS_CMD codebuild --region $REGION delete-project --name $build_proj_name || true
  echo "Done."
  }

create_codebuild_project () {
  build_proj_name=$1
  app_path=$2

  echo "========== $build_proj_name ==============="
  echo "app_path:$app_path"
  # echo "Deleting $build_proj_name from CodeBuild ..."
  $AWS_CMD codebuild --region $REGION delete-project --name $build_proj_name || true
  echo "Done."
  sleep 1

  echo "Re-creating $build_proj_name into CodeBuild ..."
  sed -e "s|__app_name__|${build_proj_name}|g;s|__app_path__|${app_path}|g;s|__Stage__|${Stage}|g;s|__METHOD__|${METHOD}|g;s|__AWS_REGION__|${REGION}|g;" \
            ./codebuild-template-offline-codecommit.json > ./codebuild.json

  if [[ $REGION =~ cn.* ]];then
     sed -i -e 's#amazonaws.com#amazonaws.com.cn#g' ./codebuild.json
  fi

  echo "------------------------------------"
#  echo ""
#  cat codebuild.json
#  echo ""
#  echo "------------------------------------"

  $AWS_CMD codebuild --region $REGION create-project \
    --cli-input-json file://codebuild.json \
    --service-role ${roleArn} > /dev/null

  if [[ $? != 0 ]];then
     echo "Error run aws codebuild create-project"
     exit 1
  fi

  sleep 1

  rm -f codebuild.json

  echo "Start build: ${build_proj_name}"
  $AWS_CMD codebuild start-build --region $REGION --project-name ${build_proj_name} > /dev/null
  if [[ $? != 0 ]];then
         echo "Error run aws codebuild start-build"
         exit 1
  fi
}

sleep 10

echo "----------------projects-------------------------"

lambda_project="lambda"
build_name=${lambda_project}
build_proj_name="rs-$Stage-offline-${build_name}-build"
app_path=${lambda_project}
if [[ $DELETE_FLAG == 'DELETE' ]];then
    delete_codebuild_project $build_proj_name $app_path
else
    create_codebuild_project $build_proj_name $app_path
fi

projects_dir=(
  "item-preprocessing"
  "add-item-batch"
  "item-feature-update-batch"
  "model-update-embedding"
  "prepare-training-data"
  "model-update-action"
  "dashboard"
  "action-preprocessing"
  "user-preprocessing"
  "batch-preprocessing"
  "add-user-batch"
  "portrait-batch"
  "recall-batch"
  "rank-batch"
  "filter-batch"
  "inverted-list"
  "step-funcs"
  "model-update-deepfm"
  "model-update-ub"
)


for project in ${projects_dir[@]}; do
  build_name="${SCENARIO}-${project}"
  build_proj_name="rs-$Stage-offline-${build_name}-build"
  if [[ -n $CN_REGION ]];then
    build_proj_name="rs-$Stage-offline-${build_name}-$CN_REGION-build"
  fi
  app_path="${SCENARIO}/${project}"
  if [[ -d "${cur_dir}/../../src/offline/${app_path}" ]];then
    if [[ $DELETE_FLAG == 'DELETE' ]];then
      delete_codebuild_project $build_proj_name $app_path
    else
      create_codebuild_project $build_proj_name $app_path
    fi
  fi
done

