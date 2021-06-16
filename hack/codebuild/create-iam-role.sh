#!/bin/bash

ROLE_NAME=rs-codebuild-role
ROLE_POLICY=rs-codebuild-policy


aws iam --profile $PROFILE get-role --role-name ${ROLE_NAME} || error=true
if [ ${error} ]
then
    echo "Nothing has been done and all clear."
else
    aws iam --profile $PROFILE list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'
    for policyArn in `aws iam list-attached-role-policies --role-name ${ROLE_NAME} | jq -r '.AttachedPolicies[].PolicyArn'`
    do 

        aws iam --profile $PROFILE detach-role-policy \
            --role-name ${ROLE_NAME} \
            --policy-arn ${policyArn}
        echo "Detached ${ROLE_NAME} and ${policyArn}"

        count=`aws iam list-policy-versions --policy-arn ${policyArn} |jq -r '.Versions[].VersionId'|wc -l`
        if [ $count -eq '1' ]
        then
            aws iam --profile $PROFILE delete-policy --policy-arn ${policyArn} || true
        else 
            for versionId in `aws iam list-policy-versions --policy-arn ${policyArn} |jq -r '.Versions[].VersionId'`
            do 
                aws iam --profile $PROFILE delete-policy-version \
                    --policy-arn ${policyArn} \
                    --version-id ${versionId}
                echo "Deleted ${ROLE_POLICY} = ${policyArn} : ${versionId}" || true
            done
            aws iam --profile $PROFILE delete-policy --policy-arn ${policyArn}
        fi

    done

    # aws iam --profile $PROFILE delete-policy --policy-arn ${policyArn} || true
    aws iam --profile $PROFILE delete-role \
        --role-name ${ROLE_NAME}
    echo "Deleted ${ROLE_NAME}"

fi
if [ $? -ne 0 ] 
then
    echo "Failed to delete role : exit 0"
    exit 0
fi

roleArn=`aws iam --profile $PROFILE create-role \
    --role-name ${ROLE_NAME} \
    --assume-role-policy-document file://assume-role.json | jq -r '.Role.Arn'`
echo "Created ${ROLE_NAME} = ${roleArn}"

rolePolicyArn=`aws iam --profile $PROFILE create-policy \
    --policy-name ${ROLE_POLICY} \
    --policy-document file://iam-role-policy.json | jq -r '.Policy.Arn'`
echo "Created ${ROLE_POLICY} = ${rolePolicyArn}"

aws iam attach-role-policy --profile $PROFILE \
    --role-name ${ROLE_NAME} \
    --policy-arn ${rolePolicyArn}
echo "Atteched ${rolePolicyArn} to ${ROLE_NAME} "
if [ $? -ne 0 ] 
then
    echo "Failed to create role : exit 0"
    exit 0
fi


echo ${roleArn}>role.arn