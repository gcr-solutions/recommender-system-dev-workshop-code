#!/usr/bin/env bash
set -e

export SECRET_NAME=gcr-rs-dev-workshop-secret
export APP_CONF_REPO=recommender-system-dev-workshop-code
echo "APP_CONF_REPO: $APP_CONF_REPO"

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