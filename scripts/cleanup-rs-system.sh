#!/usr/bin/env bash
set -e

export SECRET_NAME=gcr-rs-dev-workshop-secret
export APP_CONF_REPO=recommender-system-dev-workshop-code
export METHOD=customize
export SCENARIO=news
echo "APP_CONF_REPO: $APP_CONF_REPO"

input=$1

if [ $input = "clean-offline"  ]
then
  ./clean-offline.sh
elif [ $input = "clean-online" ]
then
  ./clean-online.sh
fi
