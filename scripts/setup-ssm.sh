#!/usr/bin/env bash
set -e

ACCESS_TOKEN=$1
GITHUB_USER=$2

if [[ -z $ACCESS_TOKEN  ]]; then
   echo "Error ACCESS_TOKEN is empty"
   echo "Usage: $0 <ACCESS_TOKEN> <GITHUB_USER>"
   exit 1
fi

if [[ -z $GITHUB_USER  ]]; then
   echo "Error GITHUB_USER is empty"
   echo "Usage: $0 <ACCESS_TOKEN> <GITHUB_USER>"
   exit 1
fi

SECRET_NAME=gcr-rs-dev-workshop-github
APP_CONF_REPO=recommender-system-dev-workshop-code

echo "GITHUB_USER: $GITHUB_USER"
echo  "SECRET_NAME: $SECRET_NAME"
echo  "APP_CONF_REPO: $GITHUB_USER"

cd codebuild
# 1 Create secret manager, store github user, access token and repo name
./create-secrets.sh $SECRET_NAME  \
              $GITHUB_USER  \
              $ACCESS_TOKEN \
              $APP_CONF_REPO \
# 2 import credential into CodeBuild
./import-source-credential.sh $ACCESS_TOKEN $GITHUB_USER

