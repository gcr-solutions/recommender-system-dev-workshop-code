#!/usr/bin/env bash

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

echo "AWS_CMD: $AWS_CMD"
echo ""
sleep 5

echo "1. sync sample-data-movie ..."
$AWS_CMD s3 sync s3://aws-gcr-rs-sol-dev-ap-southeast-1-522244679887/sample-data-movie/ s3://aws-gcr-rs-sol-demo-ap-southeast-1-522244679887/sample-data-movie/

echo ""
echo "2. sync sample-data-news ..."
$AWS_CMD s3 sync s3://aws-gcr-rs-sol-dev-ap-southeast-1-522244679887/sample-data-news/ s3://aws-gcr-rs-sol-demo-ap-southeast-1-522244679887/sample-data-news/

echo "Done"
