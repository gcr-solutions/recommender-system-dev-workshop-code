#!/usr/bin/env bash
set -e

export EKS_CLUSTER=gcr-rs-dev-workshop-cluster
EKS_VPC_ID=$(aws eks describe-cluster --name $EKS_CLUSTER --query "cluster.resourcesVpcConfig.vpcId" --output text)

echo "################ start clean online resources ################ "

echo "################ start clean EFS resource ################ "

#delete EFS file system
EFS_ID=$(aws efs describe-file-systems | jq '.[][] | select(.Tags[].Value=="GCR-RS-DEV-WORKSHOP-EFS-FileSystem")' | jq '.FileSystemId' -r)
if [ "$EFS_ID" != "" ]; then
  for EFS_SUB_ID in $(echo $EFS_ID); do
    MOUNT_TARGET_IDS=$(aws efs describe-mount-targets --file-system-id $EFS_SUB_ID | jq '.[][].MountTargetId' -r)
    for MOUNT_TARGET_ID in $(echo $MOUNT_TARGET_IDS); do
      echo remove $MOUNT_TARGET_ID
      aws efs delete-mount-target --mount-target-id $MOUNT_TARGET_ID
    done
  
    MOUNT_TARGET_IDS=""
    while true; do
      MOUNT_TARGET_IDS=$(aws efs describe-mount-targets --file-system-id $EFS_SUB_ID | jq '.[][].MountTargetId' -r)
      if [ "$MOUNT_TARGET_IDS" == "" ]; then
        echo "delete GCR-RS-DEV-WORKSHOP-EFS-FileSystem EFS mount target successfully!"
        break
      else
        echo "deleting GCR-RS-DEV-WORKSHOP-EFS-FileSystem EFS mount target!"
      fi
      sleep 20
    done
  
    echo remove EFS File System: $EFS_SUB_ID
   
   
    echo remove $EFS_SUB_ID
    aws efs delete-file-system --file-system-id $EFS_SUB_ID
  done

  EFS_ID=""
  while true; do
    EFS_ID=$(aws efs describe-file-systems | jq '.[][] | select(.Tags[].Value=="GCR-RS-DEV-WORKSHOP-EFS-FileSystem")' | jq '.FileSystemId' -r)
    if [ "$EFS_ID" == "" ]; then
      echo "delete GCR-RS-DEV-WORKSHOP-EFS-FileSystem EFS successfully!"
      break
    else
      echo "deleting GCR-RS-DEV-WORKSHOP-EFS-FileSystem EFS!"
    fi
    sleep 20
  done
fi

#delete EFS file system security group
NFS_SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters Name=vpc-id,Values=$EKS_VPC_ID Name=group-name,Values=gcr-rs-dev-workshop-efs-nfs-sg | jq '.SecurityGroups[].GroupId' -r)

if [ "$NFS_SECURITY_GROUP_ID" != "" ]; then
  echo remove security group $NFS_SECURITY_GROUP_ID
  aws ec2 delete-security-group --group-id $NFS_SECURITY_GROUP_ID
fi

#delete Elastic Cache Redis
echo "################ start clean Elasticache Redis resources ################ "
ELASTIC_CACHE_CLUSTER=$(aws elasticache describe-cache-clusters | jq '.CacheClusters[] | select(.CacheClusterId=="gcr-rs-dev-workshop-redis-cluster")')
if [ "$ELASTIC_CACHE_CLUSTER" != "" ]; then
  aws elasticache delete-cache-cluster --cache-cluster-id gcr-rs-dev-workshop-redis-cluster
  while true; do
    ELASTIC_CACHE_CLUSTER=$(aws elasticache describe-cache-clusters | jq '.CacheClusters[] | select(.CacheClusterId=="gcr-rs-dev-workshop-redis-cluster")')
    if [ "$ELASTIC_CACHE_CLUSTER" == "" ]; then
      echo "delete gcr-rs-dev-workshop-redis-cluster successfully!"
      break
    else
      echo "deleting gcr-rs-dev-workshop-redis-cluster!"
    fi
    sleep 20
  done
  aws elasticache delete-cache-subnet-group --cache-subnet-group-name gcr-rs-dev-workshop-redis-subnet-group
fi

#delete REDIS Cache security group
REDIS_SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters Name=vpc-id,Values=$EKS_VPC_ID Name=group-name,Values=gcr-rs-dev-workshop-redis-sg | jq '.SecurityGroups[].GroupId' -r)
if [ "$REDIS_SECURITY_GROUP_ID" != "" ]; then
  echo delete redis security group $REDIS_SECURITY_GROUP_ID
  aws ec2 delete-security-group --group-id $REDIS_SECURITY_GROUP_ID
fi

#clean argocd and istio resources
./cleanup-argocd-istio.sh

#detach eks cluster roles
echo "################ Detach eks cluster roles ################ "

ROLE_NAMES=$(aws iam list-roles | jq '.[][].RoleName' -r | grep eksctl-gcr-rs-dev-workshop-cluster*)
for ROLE_NAME in $(echo $ROLE_NAMES); do
  POLICY_ARNS=$(aws iam list-attached-role-policies --role-name $ROLE_NAME | jq '.[][].PolicyArn' -r)
  for POLICY_ARN in $(echo $POLICY_ARNS); do
    echo detach policy $POLICY_ARN for role $ROLE_NAME
    aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn $POLICY_ARN
  done
  # echo delete role $ROLE_NAME
  # aws iam delete-role --role-name $ROLE_NAME
done

#remove eks cluster
echo "################ Delete eks cluster ################ "
eksctl delete cluster --name=$EKS_CLUSTER

#remove codebuild project
projects[0]="loader"
projects[1]="event"
projects[2]="filter"
projects[3]="portrait"
projects[4]="rank"
projects[5]="retrieve"
projects[6]="recall"
projects[7]="demo"
projects[8]="ui"

for project in ${projects[@]}
do 
    echo "Deleting ${project} from CodeBuild ..."
    aws codebuild delete-project --name gcr-rs-dev-workshop-${project}-build || true
    echo "Done."
    sleep 5
done

#delete codebuild role and policy
echo "Clean codebuild role: gcr-rs-dev-workshop-codebuild-role, policy:gcr-rs-dev-workshop-codebuild-policy"
ROLE_NAME=gcr-rs-dev-workshop-codebuild-role
ROLE_POLICY=gcr-rs-dev-workshop-codebuild-policy

ROLE_NAMES=$(aws iam list-roles | jq '.[][] | select(.RoleName=="gcr-rs-dev-workshop-codebuild-role")')
if [ "$ROLE_NAMES" == "" ]
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
echo "Clean codebuild role: gcr-rs-dev-workshop-codebuild-role and policy:gcr-rs-dev-workshop-codebuild-policy done!"
