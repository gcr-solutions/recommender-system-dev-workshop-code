#!/usr/bin/env bash

echo "################"
AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

echo "AWS_CMD: $AWS_CMD"
echo ""
sleep 5

$AWS_CMD s3 rm  s3://aws-gcr-rs-sol-dev-ap-southeast-1-522244679887/sample-data-news/ --recursive
$AWS_CMD s3 rm  s3://aws-gcr-rs-sol-demo-ap-southeast-1-522244679887/sample-data-news/ --recursive




