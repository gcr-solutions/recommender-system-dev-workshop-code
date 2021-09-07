#!/usr/bin/env bash
set -e

# Create secrets into Secret Manager
# Name for the secret
SECRET_NAME=$1
APP_CONF_REPO=$2

echo "Start to create secret"
SECRET_LIST=$(aws secretsmanager list-secrets | jq '.SecretList[] | select(.Name=="gcr-rs-dev-workshop-secret")')
if [ "$SECRET_LIST" != "" ]
then
    aws secretsmanager update-secret --secret-id $SECRET_NAME \
        --secret-string '{"appConfRepo":"'$APP_CONF_REPO'"}'
else 
    aws secretsmanager create-secret --name $SECRET_NAME \
        --secret-string '{"appConfRepo":"'$APP_CONF_REPO'"}'
fi
echo "Create secret successfully"