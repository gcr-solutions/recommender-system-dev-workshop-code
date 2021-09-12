#!/usr/bin/env bash
set -e

export EKS_CLUSTER=gcr-rs-dev-application-cluster

echo "REGION:$REGION"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID:$AWS_ACCOUNT_ID"

istio_link="https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/eks/istio-1.9.1.zip"

# 1. Create EKS Cluster
# # 1.1 Provision EKS cluster
if [[ $REGION =~ ^cn.* ]]; then
  cat ./eks/nodes-config-cn-template.yaml | sed 's/__AWS_REGION__/'"$REGION"'/g' >./eks/nodes-config.yaml
  istio_link=https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/istio-1.9.1.zip

else
  if [[ $REGION =~ us-east* ]]; then
    availabilityZones="availabilityZones: ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1f']"
    sed -e "s|__AWS_REGION__|$REGION|g;s|#__AVAILABILITYZONE__#|$availabilityZones|g" \
      ./eks/nodes-config-template.yaml >./eks/nodes-config.yaml
  else
    sed -e "s|__AWS_REGION__|$REGION|g;s|#__AVAILABILITYZONE__#|$availabilityZones|g" \
      ./eks/nodes-config-template.yaml >./eks/nodes-config.yaml
  fi
fi

eksctl create cluster -f ./eks/nodes-config.yaml

# # 1.2 Create EKS cluster namespace
kubectl apply -f ../manifests/envs/news-dev/ns.yaml

# 2. Install Istio with default profile
# curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.9.1 TARGET_ARCH=x86_64 sh -
rm -rf tmp_istio >/dev/null 2>&1
mkdir tmp_istio && cd ./tmp_istio
curl -LO $istio_link
unzip istio-1.9.1.zip && rm istio-1.9.1.zip
cd ./bin
./istioctl operator init
kubectl create ns istio-system
cd ../..
rm -rf tmp_istio

kubectl apply -f ../manifests/istio-ingress-gateway.yaml

# 3. Create EFS
# 3.1 Find vpc id, vpc cidr, subnet ids
EKS_VPC_ID=$(aws eks describe-cluster --name $EKS_CLUSTER --query "cluster.resourcesVpcConfig.vpcId" --output text)
EKS_VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids $EKS_VPC_ID --query "Vpcs[].CidrBlock" --output text)
SUBNET_IDS=$(aws ec2 describe-instances --filters Name=vpc-id,Values=$EKS_VPC_ID --query \
  'Reservations[*].Instances[].SubnetId' \
  --output text)

echo $EKS_VPC_ID
echo $EKS_VPC_CIDR
echo $SUBNET_IDS

# 3.2 Install EFS CSI driver
if [[ $REGION =~ ^cn.* ]]; then
  #curl -OL https://raw.githubusercontent.com/kubernetes-sigs/aws-efs-csi-driver/v1.3.2/docs/iam-policy-example.json
  curl -LO https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/iam-policy-example.json

  aws iam delete-policy --policy-arn arn:aws-cn:iam::$AWS_ACCOUNT_ID:policy/AmazonEKS_EFS_CSI_Driver_Policy >/dev/null 2>&1 || true

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

# 3.3 Create EFS
EFS_ID=$(aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=${efs_name} \
  --encrypted | jq '.FileSystemId' -r)

echo "EFS_ID: $EFS_ID"

# 3.4 Create NFS Security Group
NFS_SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name ${nfs_security_group_name} \
  --description "Allow NFS traffic for EFS" \
  --vpc-id $EKS_VPC_ID | jq '.GroupId' -r)

echo "NFS_SECURITY_GROUP_ID: $NFS_SECURITY_GROUP_ID"

# 3.5 add ingress rule for NFS_SECURITY_GROUP_ID before next steps
aws ec2 authorize-security-group-ingress --group-id $NFS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 2049 \
  --cidr $EKS_VPC_CIDR

sleep 2m

# 3.6 Create EFS mount targets
for subnet_id in $(echo $SUBNET_IDS); do
  aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id $subnet_id \
    --security-group $NFS_SECURITY_GROUP_ID
done

# 3.7 Apply & create PV/StorageClass
cd ../manifests/envs/news-dev/efs
cp csi-env-template.yaml csi-env.yaml
sed -i 's/FILE_SYSTEM_ID/'"$EFS_ID"'/g' csi-env.yaml
cat csi-env.yaml
docker pull public.ecr.aws/t8u1z3c8/k8s.gcr.io/kustomize/kustomize:v3.8.7
docker run --rm --entrypoint /app/kustomize --workdir /app/src -v $(pwd):/app/src public.ecr.aws/t8u1z3c8/k8s.gcr.io/kustomize/kustomize:v3.8.7 build . | kubectl apply -f -
cd ../../../../scripts

# 4 Create redis elastic cache, Provision Elasticache - Redis / Cluster Mode Disabled
# 4.1 Create subnet groups
ids=$(echo $SUBNET_IDS | xargs -n1 | sort -u | xargs \
  aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name "gcr-rs-dev-workshop-redis-subnet-group" \
  --cache-subnet-group-description "gcr-rs-dev-workshop-redis-subnet-group" \
  --subnet-ids)
echo $ids

CACHE_SUBNET_GROUP_NAME=$(echo $ids | jq '.CacheSubnetGroup.CacheSubnetGroupName' -r)
echo $CACHE_SUBNET_GROUP_NAME

# 4.2 Create redis security group
REDIS_SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name gcr-rs-dev-workshop-redis-sg \
  --description "Allow traffic for Redis" \
  --vpc-id $EKS_VPC_ID | jq '.GroupId' -r)
echo $REDIS_SECURITY_GROUP_ID

# 4.3 config security group port
aws ec2 authorize-security-group-ingress --group-id $REDIS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 6379 \
  --cidr $EKS_VPC_CIDR

# 4.4 create elastic cache redis
aws elasticache create-cache-cluster \
  --cache-cluster-id gcr-rs-dev-workshop-redis-cluster \
  --cache-node-type cache.r5.xlarge \
  --engine redis \
  --engine-version 6.x \
  --num-cache-nodes 1 \
  --cache-parameter-group default.redis6.x \
  --security-group-ids $REDIS_SECURITY_GROUP_ID \
  --cache-subnet-group-name $CACHE_SUBNET_GROUP_NAME
