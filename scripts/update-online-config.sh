#!/usr/bin/env bash
set -e

# 1 update redis config
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --cache-cluster-id gcr-rs-workshop-redis-cluster --show-cache-node-info \
--query "CacheClusters[].CacheNodes[].Endpoint.Address" --output text)
cd ../manifests/envs/news-dev
sed -i 's/REDIS_HOST_PLACEHOLDER/'"$REDIS_ENDPOINT"'/g' config.yaml

# 2 update kubernetes config map
if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "REGION: $REGION"
echo "ACCOUNT_ID: $ACCOUNT_ID"

cat config.yaml | sed 's/__AWS_REGION__/'"$REGION"'/g' > config_1.yaml
cat config_1.yaml | sed 's/__AWS_ACCOUNT_ID__/'"$ACCOUNT_ID"'/g' >  config.yaml
rm config_1.yaml

cat config.yaml
sleep 10