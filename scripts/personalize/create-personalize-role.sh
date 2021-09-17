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

if [[ $REGION =~ cn.* ]];then
  sed -e "s|__Stage__|$Stage|g;s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
            ./role/personalize-access-s3-role-template-cn.json > ./role/personalize-policy.json
else
  sed -e "s|__Stage__|$Stage|g;s|__REGION__|$REGION|g;s|__AccountID__|$AWS_ACCOUNT_ID|g" \
              ./role/personalize-access-s3-role-template.json > ./role/personalize-policy.json
fi

ROLE_NAME=gcr-rs-personalize-role
ROLE_POLICY=gcr-rs-personalize-policy

rolePolicyArn=$(aws iam list-policies | jq '.[][] | select(.PolicyName=="gcr-rs-personalize-policy")' | jq '.Arn' -r)
if [[ "${rolePolicyArn}" == "" ]]; then
  echo "-----Create Policy for Personalize Service-------"
  rolePolicyArn=`aws iam create-policy \
      --policy-name ${ROLE_POLICY} \
      --policy-document file://./role/personalize-policy.json | jq -r '.Policy.Arn'`
fi

roleArn=$(aws iam list-roles | jq '.[][] | select(.RoleName=="gcr-rs-personalize-role")' | jq '.Arn' -r)
if [[ "${roleArn}" == "" ]]; then
  echo "-----Create Role for Personalize Service-------"
  roleArn=`aws iam create-role \
      --role-name ${ROLE_NAME} \
      --assume-role-policy-document file://./role/assume-role.json | jq -r '.Role.Arn'`
  echo "Created ${ROLE_NAME} = ${roleArn}"
fi

attachedRolePolicy=$(aws iam list-attached-role-policies --role-name $ROLE_NAME | \
                    jq '.[][] | select(.PolicyName=="gcr-rs-personalize-role")' | jq '.PolicyArn' -r)
if [[ "${attachedRolePolicy}" == "" ]]; then
  echo "-----Attach Personalize Policy to Personalize Role------"
  aws iam attach-role-policy \
      --role-name ${ROLE_NAME} \
      --policy-arn ${rolePolicyArn}
fi


echo "-----Attach Personalize Policy to S3------"

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