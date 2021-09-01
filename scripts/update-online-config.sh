#!/usr/bin/env bash
set -e

if [[ $REGION=～ ^cn.* ]];then
  export AWS_PROFILE=$REGION=～ ^cn.*
  export REGION=$(aws configure get region)
fi

# 1 update redis config
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --cache-cluster-id gcr-rs-dev-workshop-redis-cluster --show-cache-node-info \
--query "CacheClusters[].CacheNodes[].Endpoint.Address" --output text)
echo $REDIS_ENDPOINT
cd ../manifests/envs/news-dev
cat config-template.yaml | sed 's/__REDIS_HOST_PLACEHOLDER__/'"$REDIS_ENDPOINT"'/g' > config_1.yaml

# 2 update kubernetes config map
if [[ -z $REGION ]];then
    REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r '.region')
fi

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "REGION: $REGION"
echo "ACCOUNT_ID: $ACCOUNT_ID"

cat config_1.yaml | sed 's/__AWS_REGION__/'"$REGION"'/g' > config_2.yaml
cat config_2.yaml | sed 's/__AWS_ACCOUNT_ID__/'"$ACCOUNT_ID"'/g' >  config.yaml
rm config_1.yaml
rm config_2.yaml

cat config.yaml
sleep 10