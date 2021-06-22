#!/usr/bin/env bash
set -e

# Create secrets into Secret Manager
# Name for the secret
SECRET_NAME=$1
GITHUB_USER=$2
ACCESS_TOKEN=$3
APP_CONF_REPO=$4

echo "Start to create secret"
SECRET_LIST=$(aws secretsmanager list-secrets | jq '.SecretList[] | select(.Name=="gcr-rs-dev-workshop-github")')
if [ "$SECRET_LIST" != "" ]
then
    aws secretsmanager update-secret --secret-id $SECRET_NAME \
        --secret-string '{"githubUser":"'$GITHUB_USER'", "accessToken":"'$ACCESS_TOKEN'", "appConfRepo":"'$APP_CONF_REPO'"}'
else 
    aws secretsmanager create-secret --name $SECRET_NAME \
        --secret-string '{"githubUser":"'$GITHUB_USER'", "accessToken":"'$ACCESS_TOKEN'", "appConfRepo":"'$APP_CONF_REPO'"}'
fi
echo "Create secret successfully"