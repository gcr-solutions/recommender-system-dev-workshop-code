# Create EFS
# 1 Find vpc id, vpc cidr, subnet ids
EKS_VPC_ID=$(aws eks --profile $PROFILE describe-cluster --name $EKS_CLUSTER --region $REGION --query "cluster.resourcesVpcConfig.vpcId" --output text)
EKS_VPC_CIDR=$(aws ec2  --profile $PROFILE describe-vpcs --vpc-ids $EKS_VPC_ID --region $REGION --query "Vpcs[].CidrBlock" --output text)
SUBNET_IDS=$(aws ec2 --profile $PROFILE describe-instances --filters Name=vpc-id,Values=$EKS_VPC_ID --region $REGION --query \
  'Reservations[*].Instances[].SubnetId' \
  --output text)

echo $EKS_VPC_ID
echo $EKS_VPC_CIDR
echo $SUBNET_IDS

# 2 Install EFS CSI driver 
kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.1"

# 3 Create EFS
EFS_ID=$(aws efs  --profile $PROFILE create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --region $REGION \
  --tags Key=Name,Value=RS-EFS-FileSystem \
  --encrypted |jq '.FileSystemId' -r)


# 4 Create NFS Security Group
NFS_SECURITY_GROUP_ID=$(aws ec2 --profile $PROFILE create-security-group --group-name efs-nfs-sg \
  --description "Allow NFS traffic for EFS" \
  --region $REGION \
  --vpc-id $EKS_VPC_ID |jq '.GroupId' -r)

# 5 add ingress rule for NFS_SECURITY_GROUP_ID before next steps
aws ec2 --profile $PROFILE authorize-security-group-ingress --group-id $NFS_SECURITY_GROUP_ID \
  --region $REGION \
  --protocol tcp \
  --port 2049 \
  --cidr $EKS_VPC_CIDR

# 6 Create EFS mount targets
for subnet_id in `echo $SUBNET_IDS`
do
  aws efs --profile $PROFILE create-mount-target \
    --file-system-id $EFS_ID \
    --region $REGION \
    --subnet-id $subnet_id \
    --security-group $NFS_SECURITY_GROUP_ID
done

# 7 Apply & create PV/StorageClass
cd ../manifests/efs
sed -i .backup 's/FILE_SYSTEM_ID/'"$EFS_ID"'/g' csi-env.yaml
cat csi-env.yaml
kustomize build . |kubectl apply -f - 
mv csi-env.yaml.backup csi-env.yaml
cd ../../hack