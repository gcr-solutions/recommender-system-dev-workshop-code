#!/usr/bin/env bash
set -e

Stage=$1
paramDelete=$2

if [[ -z $SCENARIO ]]; then
  SCENARIO='news'
fi

if [[ -z $Stage ]];then
   Stage='dev-workshop'
fi

echo "Stage: $Stage"
echo "paramDelete: $paramDelete"
AWS_CMD="aws"

if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi
echo "AWS_CMD=${AWS_CMD}"

if [[ -z $REGION ]];then
  REGION=$(${AWS_CMD} configure get region)
fi

echo "REGION=$REGION"

if [[ -z $REGION ]];then
  echo "error ENV REGION is empty"
  exit 0
fi

AWS_P='aws'
if [[ $REGION =~ cn.* ]];then
  AWS_P='aws-cn'
fi

AWS_ACCOUNT_ID=$(${AWS_CMD} sts get-caller-identity --region ${REGION} --query Account --output text)
echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
ROLE_NAME=gcr-rs-personalize-role-${REGION}
echo "ROLE_NAME:$ROLE_NAME"

roleArn="arn:${AWS_P}:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo "roleArn:${roleArn}"

STACK_NAME=rs-personalize-role-stack
echo "STACK_NAME: ${STACK_NAME}"

if [[ $paramDelete == 'DELETE' ]]; then
  echo "Clean STACK_NAME: ${STACK_NAME}"
  $AWS_CMD cloudformation delete-stack --region ${REGION} --stack-name ${STACK_NAME}
  exit 0
fi

sed -e "s|__Stage__|$Stage|g;s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
              ./role/personalize-role-template.yaml > ./role/personalize-role.yaml

PARAMETER_OVERRIDES="Stage=$Stage"
$AWS_CMD  cloudformation deploy --region ${REGION} \
--template-file ./role/personalize-role.yaml --stack-name ${STACK_NAME} \
--parameter-overrides ${PARAMETER_OVERRIDES} \
--capabilities CAPABILITY_NAMED_IAM \
--no-fail-on-empty-changeset

StackStatus=$($AWS_CMD cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

if [[ $? -ne 0 ]]; then
     echo "error!!!  ${StackStatus}"
     exit 1
fi

echo ${roleArn} >_role.arn
cat _role.arn

echo "-----Attach Personalize Policy to S3------"
Bucket_Build=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
echo "Bucket=${Bucket_Build}"

if [[ $REGION =~ cn.* ]];then
  sed -e "s|__Stage__|$Stage|g;s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
            ./role/s3-bucket-policy-template-cn.json > ./role/s3-policy.json
else
  sed -e "s|__Stage__|$Stage|g;s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
              ./role/s3-bucket-policy-template.json > ./role/s3-policy.json
fi

$AWS_CMD s3api put-bucket-policy --bucket ${Bucket_Build} --policy file://./role/s3-policy.json

rm -f ./role/personalize-policy.json
rm -f ./role/s3-policy.json

echo "--------Complete creating personalize role ----------"