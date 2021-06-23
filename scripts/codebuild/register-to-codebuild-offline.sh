#!/usr/bin/env bash
#set -e
# export PROFILE=rsops
echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

DELETE_FLAG=$2
if [[ -z $DELETE_FLAG ]];then
  DELETE_FLAG='no'
fi


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

if [[ -z $GITHUB_USER ]]; then
   echo "error!!! can not get your $GITHUB_USER"
   exit 1
fi


echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
echo "GITHUB_USER: ${GITHUB_USER}"

roleArn=$(cat role.arn) ||  roleArn=''
if [[ -z $roleArn ]]; then
  #echo "ERROR: cannot read file role.arn, please set your codebuild role in file: 'role.arn' or run ./create-iam-role.sh firstly"
  roleArn="arn:aws:iam::${AWS_ACCOUNT_ID}:role/rs-codebuild-role"
  #exit 1
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
  echo "Deleting $build_proj_name from CodeBuild ..."
  $AWS_CMD codebuild --region $REGION delete-project --name $build_proj_name || true
  echo "Done."
  sleep 1

  echo "Re-creating $build_proj_name into CodeBuild ..."
  sed -e 's/__app_name__/'${build_proj_name}'/g' ./codebuild-template-offline.json >./tmp-codebuild.json
  sed -e 's#__app_path__#'${app_path}'#g' ./tmp-codebuild.json > tmp-codebuild_2.json
  sed -e 's#__Stage__#'${Stage}'#g' ./tmp-codebuild_2.json > ./tmp-codebuild_3.json
  sed -e 's#__GITHUB_USER_NAME__#'${GITHUB_USER}'#g' ./tmp-codebuild_3.json > ./codebuild.json

  echo "------------------------------------"
  echo ""
  cat codebuild.json
  echo ""
  echo "------------------------------------"

  $AWS_CMD codebuild --region $REGION create-project \
    --cli-input-json file://codebuild.json \
    --service-role ${roleArn} > /dev/null

  if [[ $? != 0 ]];then
     echo "Error run aws codebuild create-project"
     exit 1
  fi

  sleep 2

  rm -f codebuild.json
  rm -f tmp-codebuild*.json

  if [[ $app_path != 'news' &&  $app_path != 'movie' ]]; then
      echo "Start build: ${build_proj_name}"
      $AWS_CMD codebuild start-build --region $REGION --project-name ${build_proj_name} > /dev/null
      if [[ $? != 0 ]];then
         echo "Error run aws codebuild start-build"
         exit 1
      fi

#     echo "Activing webhook on Github with all events ..."
#     $AWS_CMD codebuild --region $REGION create-webhook \
#           --project-name $build_proj_name \
#           --filter-groups '[
#               [{"type": "EVENT", "pattern": "PUSH", "excludeMatchedPattern": false},
#                {"type":"FILE_PATH", "pattern": "src/offline/'${app_path}'", "excludeMatchedPattern": false}]
#           ]'
  fi
}

echo "----------------projects-------------------------"

projects_dir=(
  "lambda"
  "news/action-preprocessing"
  "news/prepare-training-data"
  "news/user-preprocessing"
  "news/add-item-batch"
  "news/add-user-batch"
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
  "news/step-funcs"
  "news"
)

for project in ${projects_dir[@]}; do
  build_name=$(echo ${project} | sed 's#/#-#g')
  build_proj_name="rs-$Stage-offline-${build_name}-build"
  app_path=${project}
  if [[ $DELETE_FLAG == 'DELETE' ]];then
      delete_codebuild_project $build_proj_name $app_path
  else
      create_codebuild_project $build_proj_name $app_path
  fi
done

echo "Please check result in codebuild:"
echo "search 'rs-$Stage-offline-'"
echo "https://$REGION.console.aws.amazon.com/codesuite/codebuild/projects?region=$REGION"
echo ""
echo "Done"

