#!/usr/bin/env bash
set -e

export EKS_CLUSTER=gcr-rs-dev-application-cluster

ns_name=rs-news-dev-ns
istio_system_name=istio-system
csi_driver_name=efs.csi.aws.com
efs_name=GCR-RS-DEV-WORKSHOP-EFS-FileSystem
nfs_security_group_name=gcr-rs-dev-workshop-efs-nfs-sg
pv_name=efs-pv-news-dev
cache_subnet_group_name=gcr-rs-dev-workshop-redis-subnet-group
redis_security_group_name=gcr-rs-dev-workshop-redis-sg
cache_cluster_id=gcr-rs-dev-workshop-redis-cluster

echo "REGION:$REGION"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION}  --query Account --output text)

echo "AWS_ACCOUNT_ID:$AWS_ACCOUNT_ID"

istio_link="https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/eks/istio-1.9.1.zip"

# 1. Create EKS Cluster
# # 1.1 Provision EKS cluster 
if [[ $REGION =~ ^cn.* ]];then
  cat ./eks/nodes-config-cn-template.yaml | sed 's/__AWS_REGION__/'"$REGION"'/g' > ./eks/nodes-config.yaml
  istio_link=https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/istio-1.9.1.zip

else
  if [[ $REGION =~ us-east* ]];then
    availabilityZones="availabilityZones: ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1f']"
    sed -e "s|__AWS_REGION__|$REGION|g;s|#__AVAILABILITYZONE__#|$availabilityZones|g" \
           ./eks/nodes-config-template.yaml  > ./eks/nodes-config.yaml
  else
    sed -e "s|__AWS_REGION__|$REGION|g;s|#__AVAILABILITYZONE__#|$availabilityZones|g" \
           ./eks/nodes-config-template.yaml  > ./eks/nodes-config.yaml
  fi
fi

existed_cluster=$(eksctl get cluster | grep ${EKS_CLUSTER} || echo "")
if [[ "${existed_cluster}" == "" ]];then
  echo "Create Cluster: ${EKS_CLUSTER} ..........."
  eksctl create cluster -f ./eks/nodes-config.yaml
else
  echo "Cluster: ${EKS_CLUSTER} already exist ..........."
fi

# # 1.2 Create EKS cluster namespace
existed_ns=$(kubectl get ns | grep ${ns_name} || echo "")
if [[ "${existed_ns}" == "" ]];then
  echo "Create Namespace: ${existed_ns} ..........."
  kubectl apply -f ../manifests/envs/news-dev/ns.yaml
else
  echo "Namespace: ${ns_name} already exist ..........."
fi

# 2. Install Istio with default profile
# curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.9.1 TARGET_ARCH=x86_64 sh -
existed_istio=$(kubectl get ns | grep ${istio_system_name} || echo "")
if [[ "${existed_istio}" == "" ]];then
  echo "Create Istio-System ..........."
  rm -rf tmp_istio > /dev/null 2>&1
  mkdir tmp_istio && cd ./tmp_istio
  curl -LO $istio_link
  unzip istio-1.9.1.zip && rm istio-1.9.1.zip
  cd ./bin
  ./istioctl operator init
  kubectl create ns istio-system
  cd ../..
  rm -rf tmp_istio

  kubectl apply -f ../manifests/istio-ingress-gateway.yaml
else
  echo "Istio System: ${istio_system_name} already exist ..........."
fi


# 3. Create EFS
# 3.1 Find vpc id, vpc cidr, subnet ids
EKS_VPC_ID=$(aws eks describe-cluster --name $EKS_CLUSTER --query "cluster.resourcesVpcConfig.vpcId" --output text)
EKS_VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids $EKS_VPC_ID --query "Vpcs[].CidrBlock" --output text)
SUBNET_IDS=$(aws ec2 describe-instances --filters Name=vpc-id,Values=$EKS_VPC_ID --query \
  'Reservations[*].Instances[].SubnetId' \
  --output text)

echo "EKS_VPC_ID: $EKS_VPC_ID"
echo "EKS_VPC_CIDR: $EKS_VPC_CIDR"
echo "SUBNET_IDS: $SUBNET_IDS"

# 3.2 Install EFS CSI driver
#existed_csi_driver=$(kubectl get csidriver | grep ${csi_driver_name} || echo "")
#if [[ "${existed_csi_driver}" == "" ]];then
  echo "Create CSI Driver: ${csi_driver_name} ..........."
  if [[ $REGION =~ ^cn.* ]];then
    #curl -OL https://raw.githubusercontent.com/kubernetes-sigs/aws-efs-csi-driver/v1.3.2/docs/iam-policy-example.json
    curl -LO https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/iam-policy-example.json

    aws iam delete-policy --policy-arn arn:aws-cn:iam::$AWS_ACCOUNT_ID:policy/AmazonEKS_EFS_CSI_Driver_Policy > /dev/null 2>&1 || true

    aws iam create-policy \
        --policy-name AmazonEKS_EFS_CSI_Driver_Policy \
        --policy-document file://iam-policy-example.json

    eksctl utils associate-iam-oidc-provider --region=$REGION --cluster=$EKS_CLUSTER

    eksctl create iamserviceaccount \
        --name efs-csi-controller-sa \
        --namespace kube-system \
        --cluster $EKS_CLUSTER \
        --attach-policy-arn arn:aws-cn::$AWS_ACCOUNT_ID:policy/AmazonEKS_EFS_CSI_Driver_Policy \
        --approve \
        --override-existing-serviceaccounts \
        --region $REGION
    # install EFS driver
    kubectl appy -f ../manifests/efs/driver-efs-cn.yaml
  else
    kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.1"
  fi
#else
#  echo "CSI Driver: ${csi_driver_name} already exist ..........."
#fi

# 3.3 Create EFS
existed_EFS=$(aws efs describe-file-systems | grep ${efs_name} || echo "")
if [[ "${existed_EFS}" == "" ]];then
  echo "Create EFS: ${efs_name} ..........."
  EFS_ID=$(aws efs create-file-system \
    --performance-mode generalPurpose \
    --throughput-mode bursting \
    --tags Key=Name,Value=${efs_name} \
    --encrypted |jq '.FileSystemId' -r)

else
  echo "EFS: ${efs_name} already exist ..........."
  EFS_ID=$(aws efs describe-file-systems | jq '.[][] | select(.Name=="GCR-RS-DEV-WORKSHOP-EFS-FileSystem") | .FileSystemId' -r)
fi

echo "EFS_ID: $EFS_ID"

# 3.4 Create NFS Security Group
existed_NFS_SECURITY_GROUP=$(aws ec2 describe-security-groups | grep ${nfs_security_group_name} || echo "")
if [[ "${existed_NFS_SECURITY_GROUP}" == "" ]];then
  echo "Create NFS Security Group: ${nfs_security_group_name} ..........."
  NFS_SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name ${nfs_security_group_name} \
    --description "Allow NFS traffic for EFS" \
    --vpc-id $EKS_VPC_ID |jq '.GroupId' -r)

  # 3.5 add ingress rule for NFS_SECURITY_GROUP_ID before next steps
  aws ec2 authorize-security-group-ingress --group-id $NFS_SECURITY_GROUP_ID \
    --protocol tcp \
    --port 2049 \
    --cidr $EKS_VPC_CIDR

  sleep 2m
else
  echo "NFS Security Group: ${nfs_security_group_name} already exist ..........."
  NFS_SECURITY_GROUP_ID=$(aws ec2 describe-security-groups | jq '.[][] | select(.GroupName=="gcr-rs-dev-workshop-efs-nfs-sg") | .GroupId' -r)
fi

echo "NFS_SECURITY_GROUP_ID: $NFS_SECURITY_GROUP_ID"

# 3.6 Create EFS mount targets
existed_EFS_mount_target=$(aws efs describe-mount-targets --file-system-id ${EFS_ID} || echo "")
if [[ "${existed_EFS_mount_target}" == "" ]];then
  echo "Create EFS Mount Targets, EFS_ID: ${EFS_ID} ..........."
  for subnet_id in `echo $SUBNET_IDS`
  do
    aws efs create-mount-target \
      --file-system-id $EFS_ID \
      --subnet-id $subnet_id \
      --security-group $NFS_SECURITY_GROUP_ID
  done
else
  echo "EFS Mount Targets, File System Id: ${EFS_ID}, Security_Group: ${NFS_SECURITY_GROUP_ID} already exist ..........."
fi

# 3.7 Apply & create PV/StorageClass
existed_pv=$(kubectl get pv | grep ${pv_name} || echo "")
if [[ "${existed_pv}" == "" ]];then
  echo "Create PV: ${pv_name} ..........."
  cd ../manifests/envs/news-dev/efs
  cp csi-env-template.yaml csi-env.yaml
  sed -i 's/FILE_SYSTEM_ID/'"$EFS_ID"'/g' csi-env.yaml
  cat csi-env.yaml
  docker pull public.ecr.aws/t8u1z3c8/k8s.gcr.io/kustomize/kustomize:v3.8.7
  docker run --rm --entrypoint /app/kustomize --workdir /app/src -v $(pwd):/app/src public.ecr.aws/t8u1z3c8/k8s.gcr.io/kustomize/kustomize:v3.8.7 build . |kubectl apply -f -
  cd ../../../../scripts
else
  echo "PV/StorageClass: ${pv_name} already exist ..........."
fi

# 4 Create redis elastic cache, Provision Elasticache - Redis / Cluster Mode Disabled
# 4.1 Create subnet groups
existed_subnet_groups=$(aws elasticache describe-cache-subnet-groups | grep ${cache_subnet_group_name} || echo "")
if [[ "${existed_subnet_groups}" == "" ]];then
  echo "Create Subnet Group: ${cache_subnet_group_name} ..........."
  ids=`echo $SUBNET_IDS | xargs -n1 | sort -u | xargs \
      aws elasticache create-cache-subnet-group \
      --cache-subnet-group-name ${cache_subnet_group_name} \
      --cache-subnet-group-description ${cache_subnet_group_name} \
      --subnet-ids`
  echo $ids

else
  echo "Cache Subnet Group: ${cache_subnet_group_name} already exist ..........."
fi

echo "cache_subnet_group_name=$cache_subnet_group_name"

# 4.2 Create redis security group
existed_REDIS_SECURITY_GROUP=$(aws ec2 describe-security-groups | grep ${redis_security_group_name} || echo "")
if [[ "${existed_REDIS_SECURITY_GROUP}" == "" ]];then
  echo "Create REDIS Security Group: ${cache_subnet_group_name} ..........."
  REDIS_SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name gcr-rs-dev-workshop-redis-sg \
    --description "Allow traffic for Redis" \
    --vpc-id $EKS_VPC_ID|jq '.GroupId' -r)
  echo $REDIS_SECURITY_GROUP_ID

  # 4.3 config security group port
  echo "ec2 authorize-security-group-ingress"
  aws ec2 authorize-security-group-ingress --group-id $REDIS_SECURITY_GROUP_ID \
    --protocol tcp \
    --port 6379 \
    --cidr $EKS_VPC_CIDR
else
  echo "Redis Security Group: ${cache_subnet_group_name} already exist ..........."
fi


# 4.4 create elastic cache redis
if [[ ${REDIS_SECURITY_GROUP_ID} == "" ]];then
  REDIS_SECURITY_GROUP_ID=$(aws ec2 describe-security-groups | jq '.[][] | select(.GroupName=="gcr-rs-dev-workshop-redis-sg") | .GroupId' -r)
  echo REDIS_SECURITY_GROUP_ID: $REDIS_SECURITY_GROUP_ID
fi

existed_cache_cluster=$(aws elasticache describe-cache-clusters | grep ${cache_cluster_id} || echo "")
if [[ "${existed_cache_cluster}" == "" ]];then
  echo "Create Cache Cluster: ${cache_cluster_id} ..........."
  aws elasticache create-cache-cluster \
    --cache-cluster-id ${cache_cluster_id} \
    --cache-node-type cache.r5.xlarge \
    --engine redis \
    --engine-version 6.x \
    --num-cache-nodes 1 \
    --cache-parameter-group default.redis6.x \
    --security-group-ids $REDIS_SECURITY_GROUP_ID \
    --cache-subnet-group-name ${cache_subnet_group_name}
else
  echo "Cache Cluster: ${cache_cluster_id} already exist ..........."
fi