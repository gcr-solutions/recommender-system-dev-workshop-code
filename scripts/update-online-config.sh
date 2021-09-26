#!/usr/bin/env bash
set -e

# 1 update redis config

if [[ -z $SCENARIO ]]; then
  SCENARIO='news'
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
cat config-template.yaml | sed 's/REDIS_HOST_PLACEHOLDER/'"$REDIS_ENDPOINT"'/g' > config_1.yaml

echo "REGION: $REGION"
echo "ACCOUNT_ID: $ACCOUNT_ID"

cat config_1.yaml | sed 's/__AWS_REGION__/'"$REGION"'/g' > config_2.yaml
cat config_2.yaml | sed 's/__AWS_ACCOUNT_ID__/'"$ACCOUNT_ID"'/g' >  config.yaml
rm config_1.yaml
rm config_2.yaml

cat config.yaml
sleep 10