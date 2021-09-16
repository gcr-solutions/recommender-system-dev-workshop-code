#!/usr/bin/env bash

echo "################"
echo "run $0 ..."
pwd

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi


if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

echo "REGION: $REGION"

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity  --o text | awk '{print $1}')
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

if [[ -z $RS_SCENARIO  ]];then
    RS_SCENARIO=news
fi
echo "RS_SCENARIO: $RS_SCENARIO"

BUCKET=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
S3Prefix=sample-data-$RS_SCENARIO

echo "aws  s3 rm s3://${BUCKET}/${S3Prefix}  --recursive"
$AWS_CMD s3 rm s3://${BUCKET}/ --recursive > /dev/null
$AWS_CMD s3api delete-bucket --bucket ${BUCKET}

