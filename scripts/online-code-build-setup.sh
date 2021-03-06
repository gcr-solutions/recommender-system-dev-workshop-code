#!/usr/bin/env bash
set -e

if [[ -z $SCENARIO ]]; then
  SCENARIO='news'
fi

cd codebuild

# 1 Create secret manager, store github user, access token and repo name
./create-secrets.sh $SECRET_NAME  \
              $APP_CONF_REPO \
# 2 import credential into CodeBuild
# ./import-source-credential.sh $ACCESS_TOKEN $GITHUB_USER
# 3 create codebuild role
# ./create-iam-role.sh
sleep 20
# 4 create code build project for each service
./register-to-codebuild.sh $SCENARIO

cd ../


if [[  -z $NOT_PRINTING_CONTROL_C ]];then
   echo "Please stop printing the log by typing CONTROL+C "
fi
