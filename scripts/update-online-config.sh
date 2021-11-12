#!/usr/bin/env bash
set -e

# 1 update redis config

if [[ -z $SCENARIO ]]; then
  SCENARIO='news'
fi

if [[ -z $METHOD ]]; then
  METHOD='customize'
fi

while true; do
  REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --cache-cluster-id gcr-rs-dev-workshop-redis-cluster --show-cache-node-info \
  --query "CacheClusters[].CacheNodes[].Endpoint.Address" --output text)
  if [ "$REDIS_ENDPOINT" == "" ]; then
    echo "wait redis endpoint to create!"
  else
    echo "redis create complete!"
    echo $REDIS_ENDPOINT
    break
  fi
  sleep 10
done

cd ../manifests/envs/${SCENARIO}-dev

echo "REGION: $REGION"
echo "ACCOUNT_ID: $ACCOUNT_ID"

sed -e "s|REDIS_HOST_PLACEHOLDER|$REDIS_ENDPOINT|g;s|__AWS_REGION__|$REGION|g;s|__AWS_ACCOUNT_ID__|$ACCOUNT_ID|g;s|__METHOD__|$METHOD|g"  \
            ./config-template.yaml > config.yaml


cat config.yaml
sleep 10