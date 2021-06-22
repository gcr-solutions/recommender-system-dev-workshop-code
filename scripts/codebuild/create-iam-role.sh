#!/usr/bin/env bash
set -e

ROLE_NAME=gcr-rs-dev-workshop-codebuild-role
ROLE_POLICY=gcr-rs-dev-workshop-codebuild-policy

echo "Start to create codebuild role"
ROLE_NAMES=$(aws iam list-roles | jq '.[][] | select(.RoleName=="gcr-rs-dev-workshop-codebuild-role")')
if [ ${error} ]
then
    echo "Nothing has been done and all clear."
else
    aws iam list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'
    for policyArn in `aws iam list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'`
    do 
        aws iam detach-role-policy \
            --role-name ${ROLE_NAME} \
            --policy-arn ${policyArn}
        echo "Detached ${ROLE_NAME} and ${policyArn}"

        count=`aws iam list-policy-versions --policy-arn ${policyArn} |jq -r '.Versions[].VersionId'|wc -l`
        if [ $count -eq '1' ]
        then
            aws iam delete-policy --policy-arn ${policyArn} || true
        else 
            for versionId in `aws iam list-policy-versions --policy-arn ${policyArn} |jq -r '.Versions[].VersionId'`
            do 
                aws iam delete-policy-version \
                    --policy-arn ${policyArn} \
                    --version-id ${versionId}
                echo "Deleted ${ROLE_POLICY} = ${policyArn} : ${versionId}" || true
            done
            aws iam delete-policy --policy-arn ${policyArn}
        fi
    done

    aws iam delete-role --role-name ${ROLE_NAME}
    echo "Deleted ${ROLE_NAME}"
fi
if [ $? -ne 0 ] 
then
    echo "Failed to delete role : exit 0"
    exit 0
fi

roleArn=`aws iam create-role \
    --role-name ${ROLE_NAME} \
    --assume-role-policy-document file://assume-role.json | jq -r '.Role.Arn'`
echo "Created ${ROLE_NAME} = ${roleArn}"

rolePolicyArn=`aws iam create-policy \
    --policy-name ${ROLE_POLICY} \
    --policy-document file://iam-role-policy.json | jq -r '.Policy.Arn'`
echo "Created ${ROLE_POLICY} = ${rolePolicyArn}"

aws iam attach-role-policy \
    --role-name ${ROLE_NAME} \
    --policy-arn ${rolePolicyArn}
echo "Atteched ${rolePolicyArn} to ${ROLE_NAME} "
if [ $? -ne 0 ] 
then
    echo "Failed to create role : exit 0"
    exit 0
fi

echo ${roleArn}>role.arn
echo "Create codebuild role successfully"