#!/usr/bin/env bash
set -e

if [[ -z $SCENARIO ]]; then
  SCENARIO='news'
fi

export EKS_CLUSTER=gcr-rs-dev-application-cluster

echo "REGION:$REGION"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID:$AWS_ACCOUNT_ID"

istio_link="https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/eks/istio-1.9.1.zip"

# 1. Create EKS Cluster
# # 1.1 Provision EKS cluster
echo "Create EKS Cluster ..."
if [[ $REGION =~ ^cn.* ]]; then
  cat ./eks/nodes-config-cn-template.yaml | sed 's/__AWS_REGION__/'"$REGION"'/g' >./eks/nodes-config.yaml
  istio_link=https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/istio-1.9.1.zip

else
  if [[ $REGION == "us-east-1" ]]; then
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
echo "Create EKS cluster namespace ..."
kubectl apply -f ../manifests/envs/${SCENARIO}-dev/ns.yaml

# 2. Install Istio with default profile
echo "Install Istio with default profile ..."
# curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.9.1 TARGET_ARCH=x86_64 sh -
rm -rf tmp_istio >/dev/null 2>&1
mkdir tmp_istio && cd ./tmp_istio
curl -LO $istio_link
unzip istio-1.9.1.zip > /dev/null && rm istio-1.9.1.zip
cd ./bin
./istioctl operator init
kubectl create ns istio-system
cd ../..
rm -rf tmp_istio

kubectl apply -f ../manifests/${SCENARIO}-istio-ingress-gateway.yaml

#Open istio elb 22 port for China regions
if [[ $REGION =~ ^cn.* ]];then
  echo "open 22 port for china regions [$REGION]"
  while true; do
       sleep 30
       ELB_NAME=$(aws resourcegroupstaggingapi get-resources --tag-filters Key=kubernetes.io/service-name,Values=istio-system/istio-ingressgateway-${SCENARIO}-dev |
jq -r '.ResourceTagMappingList[].ResourceARN' | cut -d'/' -f 2)
       if [[ -n $ELB_NAME ]];then
          echo "load balance name: $ELB_NAME"
          break
       else
         echo "wait for load balance ready ..."
       fi
  done


  INSTANCE_PORT=$(kubectl get svc istio-ingressgateway-${SCENARIO}-dev -n istio-system -o=jsonpath='{.spec.ports[?(@.port==80)].nodePort}')
  echo instance port: $INSTANCE_PORT

  aws elb create-load-balancer-listeners --load-balancer-name $ELB_NAME --listeners "Protocol=TCP,LoadBalancerPort=22,InstanceProtocol=TCP,InstancePort=$INSTANCE_PORT"

  ELB_SG_ID=$(aws elb describe-load-balancers --load-balancer-names $ELB_NAME | jq -r '.LoadBalancerDescriptions[].SecurityGroups[]')
  echo load balance security group id: $ELB_SG_ID

  aws ec2 authorize-security-group-ingress --group-id $ELB_SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
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
echo "REGION: $REGION"

# 3.2 Install EFS CSI driver
if [[ $REGION =~ ^cn.* ]]; then

  #curl -OL https://raw.githubusercontent.com/kubernetes-sigs/aws-efs-csi-driver/v1.3.2/docs/iam-policy-example.json
  curl -LO https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/iam-policy-example.json

  # aws iam delete-policy --policy-arn arn:aws-cn:iam::$AWS_ACCOUNT_ID:policy/AmazonEKS_EFS_CSI_Driver_Policy >/dev/null 2>&1 || true

  aws iam create-policy \
    --policy-name AmazonEKS_EFS_CSI_Driver_Policy_$REGION \
    --policy-document file://iam-policy-example.json || true

  eksctl utils associate-iam-oidc-provider --region=$REGION --cluster=$EKS_CLUSTER --approve

  echo "create iamserviceaccount ..."
  eksctl create iamserviceaccount \
    --name efs-csi-controller-sa \
    --namespace kube-system \
    --cluster $EKS_CLUSTER \
    --attach-policy-arn arn:aws-cn:iam::$AWS_ACCOUNT_ID:policy/AmazonEKS_EFS_CSI_Driver_Policy_$REGION  \
    --approve \
    --override-existing-serviceaccounts \
    --region $REGION
  # install EFS driver
  echo "apply efs/driver-efs-cn.yaml ..."
  kubectl apply -f ../manifests/efs/driver-efs-cn.yaml
else
  echo "apply kubernetes/overlays/stable/ecr/?ref=release-1.1 ..."
  kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.1"
fi

# 3.3 Create EFS
echo "create-file-system ..."
EFS_ID=$(aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=GCR-RS-DEV-WORKSHOP-EFS-FileSystem \
  --encrypted | jq '.FileSystemId' -r)

echo "EFS_ID: $EFS_ID"

# 3.4 Create NFS Security Group
echo "create-security-group --group-name gcr-rs-dev-workshop-efs-nfs-sg ..."
NFS_SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name gcr-rs-dev-workshop-efs-nfs-sg \
  --description "Allow NFS traffic for EFS" \
  --vpc-id $EKS_VPC_ID | jq '.GroupId' -r)

echo "NFS_SECURITY_GROUP_ID: $NFS_SECURITY_GROUP_ID"

# 3.5 add ingress rule for NFS_SECURITY_GROUP_ID before next steps
echo "authorize-security-group-ingress ..."
aws ec2 authorize-security-group-ingress --group-id $NFS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 2049 \
  --cidr $EKS_VPC_CIDR

sleep 2m

# 3.6 Create EFS mount targets
for subnet_id in $(echo $SUBNET_IDS); do
  echo "create-mount-target subnet-id: $subnet_id, file-system-id $EFS_ID"
  aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id $subnet_id \
    --security-group $NFS_SECURITY_GROUP_ID
done

# 3.7 Apply & create PV/StorageClass
cd ../manifests/envs/${SCENARIO}-dev/efs
cp csi-env-template.yaml csi-env.yaml
sed -i 's/FILE_SYSTEM_ID/'"$EFS_ID"'/g' csi-env.yaml
cat csi-env.yaml
docker pull public.ecr.aws/t8u1z3c8/k8s.gcr.io/kustomize/kustomize:v3.8.7
docker run --rm --entrypoint /app/kustomize --workdir /app/src -v $(pwd):/app/src public.ecr.aws/t8u1z3c8/k8s.gcr.io/kustomize/kustomize:v3.8.7 build . | kubectl apply -f -
cd ../../../../scripts

# 4 Create redis elastic cache, Provision Elasticache - Redis / Cluster Mode Disabled
# 4.1 Create subnet groups
echo "create-cache-subnet-group ..."
ids=$(echo $SUBNET_IDS | xargs -n1 | sort -u | xargs \
  aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name "gcr-rs-dev-workshop-redis-subnet-group" \
  --cache-subnet-group-description "gcr-rs-dev-workshop-redis-subnet-group" \
  --subnet-ids)

echo "cache-subnet id=$ids"

CACHE_SUBNET_GROUP_NAME=$(echo $ids | jq '.CacheSubnetGroup.CacheSubnetGroupName' -r)
echo "CACHE_SUBNET_GROUP_NAME: $CACHE_SUBNET_GROUP_NAME"

# 4.2 Create redis security group
echo "create-security-group (gcr-rs-dev-workshop-redis-sg)..."
REDIS_SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name gcr-rs-dev-workshop-redis-sg \
  --description "Allow traffic for Redis" \
  --vpc-id $EKS_VPC_ID | jq '.GroupId' -r)
echo $REDIS_SECURITY_GROUP_ID

# 4.3 config security group port
echo "authorize-security-group-ingress ..."
aws ec2 authorize-security-group-ingress --group-id $REDIS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 6379 \
  --cidr $EKS_VPC_CIDR

# 4.4 create elastic cache redis
echo "create-cache-cluster (cache-cluster-id: gcr-rs-dev-workshop-redis-cluster) ..."
aws elasticache create-cache-cluster \
  --cache-cluster-id gcr-rs-dev-workshop-redis-cluster \
  --cache-node-type cache.r5.xlarge \
  --engine redis \
  --engine-version 6.x \
  --num-cache-nodes 1 \
  --cache-parameter-group default.redis6.x \
  --security-group-ids $REDIS_SECURITY_GROUP_ID \
  --cache-subnet-group-name $CACHE_SUBNET_GROUP_NAME


echo "Online Infra Done"


if [[  -z $NOT_PRINTING_CONTROL_C ]];then
   echo "Please stop printing the log by typing CONTROL+C "
fi
