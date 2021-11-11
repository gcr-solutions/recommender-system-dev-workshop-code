#!/usr/bin/env bash
set -e

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

if [[ -z $SCENARIO ]]; then
  SCENARIO='news'
fi

echo "Stage=$Stage"
echo "REGION=$REGION"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=sample-data-${SCENARIO}

ls -l ../sample-data/notification/inverted-list/recall_config_v2.pickle

$AWS_CMD s3 cp ../sample-data/notification/inverted-list/recall_config_v2.pickle s3://${BUCKET}/${PREFIX}/notification/inverted-list/recall_config.pickle
$AWS_CMD s3 cp ../sample-data/notification/inverted-list/recall_config_v2.pickle s3://${BUCKET}/${PREFIX}/feature/content/inverted-list/recall_config.pickle

echo "Start notifying online service"

if [ $SCENARIO = news ];then
  NOTIFY_STEP_FUNC=arn:aws:states:${REGION}:${AWS_ACCOUNT_ID}:stateMachine:rs-dev-workshop-News-NotificationStepFunc
elif [ $SCENARIO = movie ];then
  NOTIFY_STEP_FUNC=arn:aws:states:${REGION}:${AWS_ACCOUNT_ID}:stateMachine:rs-dev-workshop-Movie-NotificationStepFunc
fi

echo "start-execution ${NOTIFY_STEP_FUNC} ..."

$AWS_CMD stepfunctions start-execution --state-machine-arn ${NOTIFY_STEP_FUNC} \
--input "{ \"file_type\": \"item-new\", \"Bucket\":  \"${BUCKET}\", \"S3Prefix\": \"${PREFIX}\" }"

echo "Done"

