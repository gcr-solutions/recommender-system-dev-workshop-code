#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

if [[ -z $Scenario ]];then
    Scenario='News'
fi


AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

Bucket_Build=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
echo "Bucket=${Bucket_Build}"

sed -e "s|__Stage__|$Stage|g;s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
            ./role/personalize-access-s3-role-template.json > ./role/personalize-policy.json


ROLE_NAME=gcr-rs-personalize-role
ROLE_POLICY=gcr-rs-personalize-policy

echo "Start to create personalize role"
ROLE_NAMES=$(aws iam list-roles | jq '.[][] | select(.RoleName=="gcr-rs-personalize-role")')
if [ "$ROLE_NAMES" != "" ]
then
    echo "Nothing has been done and all clear."
else
  roleArn=`aws iam create-role \
      --role-name ${ROLE_NAME} \
      --assume-role-policy-document file://./role/assume-role.json | jq -r '.Role.Arn'`
  echo "Created ${ROLE_NAME} = ${roleArn}"

  rolePolicyArn=`aws iam create-policy \
      --policy-name ${ROLE_POLICY} \
      --policy-document file://./role/personalize-policy.json | jq -r '.Policy.Arn'`
  echo "Created ${ROLE_POLICY} = ${rolePolicyArn}"

  aws iam attach-role-policy \
      --role-name ${ROLE_NAME} \
      --policy-arn ${rolePolicyArn}
  echo "Attached ${rolePolicyArn} to ${ROLE_NAME} "
  if [ $? -ne 0 ]
  then
      echo "Failed to create role : exit 0"
      exit 0
  fi

  echo ${roleArn}>role.arn
  echo "Create Personalize role successfully"
fi


echo "Start to put personalize role to S3"
sed -e "s|__Stage__|$Stage|g;s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
            ./role/s3-bucket-policy-template.json > ./role/s3-policy.json

$AWS_CMD s3api put-bucket-policy --bucket ${Bucket_Build} --policy file://./role/s3-policy.json

rm -f ./role/personalize-policy.json
rm -f ./role/s3-policy.json

echo "--------Complete creating personalize role ----------"