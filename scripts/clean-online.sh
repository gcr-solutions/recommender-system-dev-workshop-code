#!/usr/bin/env bash
#set -e

##############################delete resource for application##############################
export EKS_CLUSTER=gcr-rs-dev-application-cluster

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

##############################delete resource for application##############################

#clean argocd and istio resources
./cleanup-argocd-istio.sh

#detach eks cluster roles
echo "################ Detach eks cluster roles for workshop ################ "

ROLE_NAMES=$(aws iam list-roles | jq '.[][].RoleName' -r | grep eksctl-gcr-rs-dev-application-*)
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
echo "################ Delete eks cluster for workshop ################ "
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

echo "Please stop printing the log by typing CONTROL+C "
