#!/bin/bash

# Prerequisite 
# 1. eksctl > 0.35.0
# 2. kubectl 
# 3. awscli / configure profile for awscli

export REGION=ap-southeast-1
export EKS_CLUSTER=rs-beta
export PROFILE=rs-ops

# 1. Provision EKS cluster 
eksctl create cluster -f ./eks/x86-nodes-config.yaml --profile $PROFILE

# 2. Setup basic components
# 2.1 Install Istio with default profile
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.9.1 TARGET_ARCH=x86_64 sh -
cd ./istio-1.9.1/bin
./istioctl operator init

kubectl create ns istio-system
kubectl apply -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  namespace: istio-system
  name: default-istiocontrolplane
spec:
  profile: default
EOF

# 2.2 Install EFS CSI driver 
kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.1"

# 2.3 
# 2.3.1 Create EFS
EKS_VPC_ID=$(aws eks --profile $PROFILE describe-cluster --name $EKS_CLUSTER --query "cluster.resourcesVpcConfig.vpcId" --output text)
EKS_VPC_CIDR=$(aws ec2  --profile $PROFILE describe-vpcs --vpc-ids $EKS_VPC_ID --query "Vpcs[].CidrBlock" --output text)
EFS_ID=$(aws efs  --profile $PROFILE create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=RS-EFS-FileSystem \
  --encrypted |jq '.FileSystemId' -r)

# 2.3.2 Find subnet IDs
SUBNET_IDS=$(aws ec2 --profile $PROFILE describe-instances --filters Name=vpc-id,Values=$EKS_VPC_ID --query \
  'Reservations[*].Instances[].SubnetId' \
  --output text)

# 2.3.4 Create Security Group
NFS_SECURITY_GROUP_ID=$(aws ec2 --profile $PROFILE create-security-group --group-name efs-nfs-sg \
  --description "Allow NFS traffic for EFS" \
  --vpc-id $EKS_VPC_ID |jq '.GroupId' -r)

# add ingress rule for NFS_SECURITY_GROUP_ID before next steps
aws ec2 --profile $PROFILE authorize-security-group-ingress $NFS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 2049 \
  --cidr $EKS_VPC_CIDR

# 2.3.5 Create EFS mount targets
for subnet_id in `echo $SUBNET_IDS`
do
  aws efs --profile $PROFILE create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id $subnet_id \
    --security-group $NFS_SECURITY_GROUP_ID
done

# 2.3.6 Apply & create PV/StorageClass
cd ./manifest/efs
# TODO: sed -> replace file system ID
kustomization build . |kubectl apply -f - 

# 2.4 Provision Elasticache - Redis / Cluster Mode Disabled
# 2.4.1 Create subnet groups
# TODO $SUBNET_IDS -> "string" "string" "string"
ids=`echo $SUBNET_IDS | xargs -n1 | sort -u | xargs \
    aws elasticache --profile $PROFILE create-cache-subnet-group \
    --cache-subnet-group-name "rs-redis-subnet-group" \
    --cache-subnet-group-description "rs-redis-subnet-group" \
    --subnet-ids`
CACHE_SUBNET_GROUP_NAME=$(echo $ids |jq '.CacheSubnetGroup.CacheSubnetGroupName' -r)

# 2.4.2 Create scurity group
REDIS_SECURITY_GROUP_ID=$(aws ec2 --profile $PROFILE create-security-group --group-name rs-redis-sg \
  --description "Allow traffic for Redis" \
  --vpc-id $EKS_VPC_ID|jq '.GroupId' -r)
# Add ingress rule for REDIS_SECURITY_GROUP_ID
aws ec2 --profile $PROFILE authorize-security-group-ingress $REDIS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 6379 \
  --cidr $EKS_VPC_CIDR


# 2.4.3 Create Redis Cluster
aws elasticache --profile $PROFILE create-cache-cluster \
  --cache-cluster-id rs-redis-cluster \
  --cache-node-type cache.r6g.xlarge \
  --engine redis \
  --engine-version 6.x \
  --num-cache-nodes 1 \
  --cache-parameter-group default.redis6.x \
  --security-group-ids $REDIS_SECURITY_GROUP_ID \
  --cache-subnet-group-name $CACHE_SUBNET_GROUP_NAME


# 3. Setup CI/CD components

# 3.1 Create public registry for base images
#TODO
#public.ecr.aws

# 3.2 Setup CodeBuild for CI
#TODO
#cd codebuild
# ./create-secrets.sh github-rs  \
#               $APP_REPO_USER  \
#               $APP_REPO \
#               $APP_BRANCH \
#               $APP_CONF_REPO_USER \
#               $APP_CONF_REPO_ACCESS_TOKEN \
#               $APP_CONF_REPO  \
#               $APP_CONF_REPO_BRANCH \
#               $KMS_KEY_ID
# ./import-source-credential.sh $APP_CONF_REPO_ACCESS_TOKEN $APP_CONF_REPO_USER
# ./create-iam-role.sh
# ./register-to-codebuild.sh

# 3.2. Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
# TODO: update service type with 'LoadBalancer' & expose ArgoCD 

# 3.3 Create CD for RS in ArgoCD
# TODO / create through UI


