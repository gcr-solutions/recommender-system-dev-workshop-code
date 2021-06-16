# Provision Elasticache - Redis / Cluster Mode Disabled
# 1 Find vpc id, vpc cidr, subnet ids
EKS_VPC_ID=$(aws eks --profile $PROFILE describe-cluster --name $EKS_CLUSTER --region $REGION --query "cluster.resourcesVpcConfig.vpcId" --output text)
EKS_VPC_CIDR=$(aws ec2  --profile $PROFILE describe-vpcs --vpc-ids $EKS_VPC_ID --region $REGION --query "Vpcs[].CidrBlock" --output text)
SUBNET_IDS=$(aws ec2 --profile $PROFILE describe-instances --filters Name=vpc-id,Values=$EKS_VPC_ID --region $REGION --query \
  'Reservations[*].Instances[].SubnetId' \
  --output text)

echo $EKS_VPC_ID
echo $EKS_VPC_CIDR
echo $SUBNET_IDS  

# 2 Create subnet groups
ids=`echo $SUBNET_IDS | xargs -n1 | sort -u | xargs \
    aws elasticache --profile $PROFILE create-cache-subnet-group \
    --cache-subnet-group-name "rs-redis-subnet-group" \
    --cache-subnet-group-description "rs-redis-subnet-group" \
    --region $REGION \
    --subnet-ids`
echo $ids

CACHE_SUBNET_GROUP_NAME=$(echo $ids |jq '.CacheSubnetGroup.CacheSubnetGroupName' -r)
echo $CACHE_SUBNET_GROUP_NAME

# 3 Create redis security group
REDIS_SECURITY_GROUP_ID=$(aws ec2 --profile $PROFILE create-security-group --group-name rs-redis-sg \
  --description "Allow traffic for Redis" \
  --region $REGION \
  --vpc-id $EKS_VPC_ID|jq '.GroupId' -r)
echo $REDIS_SECURITY_GROUP_ID

# 4 config security group port
aws ec2 --profile $PROFILE authorize-security-group-ingress --group-id $REDIS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 6379 \
  --region $REGION \
  --cidr $EKS_VPC_CIDR 


# 5 create elastic cache redis
aws elasticache --profile $PROFILE create-cache-cluster \
  --cache-cluster-id rs-redis-cluster \
  --cache-node-type cache.r6g.xlarge \
  --engine redis \
  --engine-version 6.x \
  --num-cache-nodes 1 \
  --region $REGION \
  --cache-parameter-group default.redis6.x \
  --security-group-ids $REDIS_SECURITY_GROUP_ID \
  --cache-subnet-group-name $CACHE_SUBNET_GROUP_NAME