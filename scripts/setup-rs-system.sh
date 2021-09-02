#!/usr/bin/env bash
set -e

SECRET_NAME=gcr-rs-dev-workshop-github
ACCESS_TOKEN=$(aws secretsmanager get-secret-value --secret-id $SECRET_NAME  | jq -r  '.SecretString | fromjson.accessToken')
GITHUB_USER=$(aws secretsmanager get-secret-value --secret-id $SECRET_NAME  | jq -r  '.SecretString | fromjson.githubUser')

export GITHUB_USER=$GITHUB_USER
export ACCESS_TOKEN=$ACCESS_TOKEN
export APP_CONF_REPO=recommender-system-dev-workshop-code

echo "GITHUB_USER: $GITHUB_USER"
echo "APP_CONF_REPO: $APP_CONF_REPO"

if [[ -z $GITHUB_USER ]];then
  echo "Error: GITHUB_USER is empty"
  exit 1
fi

input=$1

if [ $input = "deploy-offline"  ]
then
    echo "start create offline codebuild project!"
    ./create-offline.sh
elif [ $input = "online-codebuild" ]
then
     echo "start create online codebuild project!"
    ./online-code-build-setup.sh
elif [ $input = "infra" ]
then
    echo "start create online infrastructure!"
    ./create-online-infra.sh
elif [ $input = "config" ]
then
    echo "start update online config!"
    ./update-online-config.sh
elif [ $input = "argo-server" ]
then
    echo "start setup argocd server!"
    ./setup-argocd-server.sh
elif [ $input = "application" ]
then
    echo "start create application!"
    ./create-argocd-application.sh
else
    echo "Please enter correct parameter"
fi  