#!/usr/bin/env bash
set -e

export SECRET_NAME=gcr-rs-dev-workshop-github
export GITHUB_USER=<github_user_name>
export ACCESS_TOKEN=<github_access_token>
export APP_CONF_REPO=recommender-system-dev-workshop-code

cd codebuild

# 3.1.1 Create secret manager, store github user, access token and repo name
./create-secrets.sh $SECRET_NAME  \
              $GITHUB_USER  \
              $ACCESS_TOKEN \
              $APP_CONF_REPO \
# 3.1.2 import credential into CodeBuild
./import-source-credential.sh $ACCESS_TOKEN $GITHUB_USER
# 3.1.3 create codebuild role
./create-iam-role.sh
sleep 20
# 3.1.4 create code build project for each service
./register-to-codebuild.sh

cd ../