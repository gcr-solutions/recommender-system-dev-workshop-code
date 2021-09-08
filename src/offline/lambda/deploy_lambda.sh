#!/usr/bin/env bash

echo "run $0 ..."
pwd

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -n $AWS_DEFAULT_REGION ]];then
  REGION=$AWS_DEFAULT_REGION
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

echo "AWS_CMD: $AWS_CMD"
echo "REGION: $REGION"
AWS_REGION=$REGION

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
S3Prefix=ops-data

PARAMETER_OVERRIDES="Bucket=$BUCKET S3Prefix=$S3Prefix Stage=$Stage"

STACK_NAME=rs-$Stage-role-stack
echo "STACK_NAME: ${STACK_NAME}"
$AWS_CMD  cloudformation deploy --region ${REGION} \
--template-file ./template_role.yaml --stack-name ${STACK_NAME} \
--parameter-overrides ${PARAMETER_OVERRIDES} \
--capabilities CAPABILITY_NAMED_IAM \
--no-fail-on-empty-changeset

StackStatus=$($AWS_CMD cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

if [[ $? -ne 0 ]]; then
     echo "error!!!  ${StackStatus}"
     exit 1
fi

STACK_NAME=rs-$Stage-lambda-stack
echo "STACK_NAME: ${STACK_NAME}"
echo "$AWS_CMD cloudformation deploy --region ${REGION} \
--template-file ./template.yaml --stack-name ${STACK_NAME} \
--parameter-overrides ${PARAMETER_OVERRIDES} \
--capabilities CAPABILITY_NAMED_IAM"

$AWS_CMD  cloudformation deploy --region ${REGION} \
--template-file ./template.yaml --stack-name ${STACK_NAME} \
--parameter-overrides ${PARAMETER_OVERRIDES} \
--capabilities CAPABILITY_NAMED_IAM \
--no-fail-on-empty-changeset

StackStatus=$($AWS_CMD cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

if [[ $? -ne 0 ]]; then
     echo "error!!!  ${StackStatus}"
     exit 1
fi



