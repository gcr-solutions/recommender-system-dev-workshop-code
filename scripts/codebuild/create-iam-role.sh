#!/usr/bin/env bash
set -e

Stage=$1
paramDelete=$2

if [[ -z $Stage ]];then
   Stage='dev-workshop'
fi 

echo "Stage: $Stage"
echo "paramDelete: $paramDelete"
AWS_CMD="aws --profile default"

if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi
echo "AWS_CMD=$AWS_CMD"

if [[ -z $REGION ]];then
  REGION=$($AWS_CMD configure get region)
fi

echo "REGION=$REGION"

if [[ -z $REGION ]];then
  echo "error ENV REGION is empty"
  exit 0
fi

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

ROLE_NAME=gcr-rs-${Stage}-codebuild-role
ROLE_POLICY=gcr-rs-${Stage}-codebuild-policy

echo "ROLE_NAME:$ROLE_NAME"
echo "ROLE_POLICY:$ROLE_POLICY"

function del_role() {
  $AWS_CMD iam list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'
  for policyArn in $($AWS_CMD iam list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'); do
    $AWS_CMD iam detach-role-policy \
      --role-name ${ROLE_NAME} \
      --policy-arn ${policyArn}
    echo "Detached ${ROLE_NAME} and ${policyArn}"

    count=$($AWS_CMD iam list-policy-versions --policy-arn ${policyArn} | jq -r '.Versions[].VersionId' | wc -l)
    if [ $count -eq '1' ]; then
      $AWS_CMD iam delete-policy --policy-arn ${policyArn} || true
    else
      for versionId in $($AWS_CMD iam list-policy-versions --policy-arn ${policyArn} | jq -r '.Versions[].VersionId'); do
        $AWS_CMD iam delete-policy-version \
          --policy-arn ${policyArn} \
          --version-id ${versionId}
        echo "Deleted ${ROLE_POLICY} = ${policyArn} : ${versionId}" || true
      done
      $AWS_CMD iam delete-policy --policy-arn ${policyArn}
    fi
  done

  $AWS_CMD iam delete-role --role-name ${ROLE_NAME}
  if [ $? -ne 0 ]; then
     echo "Failed to delete role : exit 0"
     exit 1
  fi
  echo "Deleted ${ROLE_NAME}"
}

if [[ $paramDelete == 'DELETE' ]]; then
    echo "Start to DELETE codebuild role"
    del_role
    exit 0
fi 

echo "Start to create codebuild role"
ROLE_NAMES=$($AWS_CMD iam list-roles | jq '.[][] | select(.RoleName=="'${ROLE_NAME}'")')
if [ "$ROLE_NAMES" == "" ]; then
  echo "Nothing has been done and all clear."
else
  echo "Delete role"
  del_role
fi

echo ""
echo "$AWS_CMD iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file://assume-role.json"

roleArn=$($AWS_CMD iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file://assume-role.json | jq -r '.Role.Arn')

echo "Created ${ROLE_NAME} = ${roleArn}"

echo ""
echo "$AWS_CMD iam create-policy \
  --policy-name ${ROLE_POLICY} \
  --policy-document file://iam-role-policy.json | jq -r '.Policy.Arn'"

rolePolicyArn=$($AWS_CMD iam create-policy \
  --policy-name ${ROLE_POLICY} \
  --policy-document file://iam-role-policy.json | jq -r '.Policy.Arn')

echo "Created ${ROLE_POLICY} = ${rolePolicyArn}"

echo ""
echo "$AWS_CMD iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn ${rolePolicyArn}"

$AWS_CMD iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn ${rolePolicyArn}
echo "Atteched ${rolePolicyArn} to ${ROLE_NAME} "
if [ $? -ne 0 ]; then
  echo "Failed to create role : exit 0"
  exit 0
fi

echo ${roleArn} >_role.arn
echo "Create codebuild role successfully"
