#!/usr/bin/env bash

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

echo "AWS_CMD: $AWS_CMD"
echo ""
sleep 5

$AWS_CMD s3 sync . s3://aws-gcr-rs-sol-dev-ap-southeast-1-522244679887/sample-data-news/
$AWS_CMD s3 sync . s3://aws-gcr-rs-sol-demo-ap-southeast-1-522244679887/sample-data-news/

$AWS_CMD s3 cp s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/dkn_embedding_latest/complete_dkn_word_embedding.npy \
 s3://aws-gcr-rs-sol-dev-ap-southeast-1-522244679887/sample-data-news/model/rank/content/dkn_embedding_latest/complete_dkn_word_embedding.npy

$AWS_CMD s3 cp s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/dkn_embedding_latest/complete_dkn_word_embedding.npy \
 s3://aws-gcr-rs-sol-demo-ap-southeast-1-522244679887/sample-data-news/model/rank/content/dkn_embedding_latest/complete_dkn_word_embedding.npy

