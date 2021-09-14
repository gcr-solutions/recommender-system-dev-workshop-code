#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"
AWS_CMD="aws"

echo "---------------"

echo "current-context:"
kubectl config current-context

echo "all contexts:"
kubectl config get-contexts

echo "---------------"

if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -n $AWS_DEFAULT_REGION && -z $REGION ]];then
  REGION=$AWS_DEFAULT_REGION
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

echo "AWS_CMD: $AWS_CMD"
echo "REGION: $REGION"

account_id=$($AWS_CMD  sts get-caller-identity --query Account --output text)

echo "account_id: $account_id"

dns_name=$(kubectl get svc istio-ingressgateway-news-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
if [[ $? != 0 ]];then
    echo "Error"
    exit 1
fi

echo "dns_name: $dns_name"

EKS_CLUSTER=gcr-rs-dev-application-cluster

botoConfig='{"user_agent_extra": "AwsSolution/SO8010/0.1.0"}'
SNS_TOPIC_ARN="arn:aws:sns:${REGION}:${account_id}:rs-$Stage-offline-sns"
echo $SNS_TOPIC_ARN

# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| join (",")'
# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| .[]'
if [[ $REGION =~ cn.* ]];then
   dns_name=$dns_name:22
fi

echo "dns_name:$dns_name"

#if [[ $REGION =~ cn.* ]];then
#   EKS_VPC_ID=$($AWS_CMD eks describe-cluster --name $EKS_CLUSTER --query "cluster.resourcesVpcConfig.vpcId" --output text)
#   SUBNET_IDS=$($AWS_CMD ec2 describe-instances --filters Name=vpc-id,Values=$EKS_VPC_ID --query \
#    'Reservations[*].Instances[].SubnetId' --output text)
#
#   SUBNET_IDS=$(echo $SUBNET_IDS | sed "s/ sub/,sub/g")
#
#   echo "EKS_VPC_ID: $EKS_VPC_ID"
#   echo "SUBNET_IDS: $SUBNET_IDS"
#
#   SG_NAME=gcr-rs-dev-workshop-lambda-sg
#
#   echo "create-security-group --group-name ${SG_NAME}  ..."
#   SG_ID=$($AWS_CMD ec2 describe-security-groups --filters Name=group-name,Values=${SG_NAME} \
#     --query "SecurityGroups[*].{Name:GroupName,ID:GroupId, VpcId:VpcId}" | jq -r '.[].ID')
#   if [[ -n $SG_ID ]];then
##      echo "delete-security-group --group-id $SG_ID "
##      $AWS_CMD ec2 delete-security-group --group-id $SG_ID
##      sleep 10
#      LAMBDA_ECURITY_GROUP_ID=$SG_ID
#   else
#       LAMBDA_ECURITY_GROUP_ID=$($AWS_CMD ec2 create-security-group --group-name ${SG_NAME} \
#       --description "SG for RS lambda" \
#       --vpc-id $EKS_VPC_ID | jq '.GroupId' -r)
#       echo "LAMBDA_ECURITY_GROUP_ID: $LAMBDA_ECURITY_GROUP_ID"
#       sleep 10
#   fi
#
#   echo "update-function-configuration"
#   $AWS_CMD lambda update-function-configuration  --function-name rs-$Stage-SNSMessageLambda \
#   --environment "Variables={NEWS_ONLINE_LOADER_URL=${dns_name},botoConfig='${botoConfig}',SNS_TOPIC_ARN='${SNS_TOPIC_ARN}'}" \
#   --vpc-config SubnetIds=$SUBNET_IDS,SecurityGroupIds=$LAMBDA_ECURITY_GROUP_ID
#
#else
#   $AWS_CMD lambda update-function-configuration  --function-name rs-$Stage-SNSMessageLambda \
#   --environment "Variables={NEWS_ONLINE_LOADER_URL=${dns_name},botoConfig='${botoConfig}',SNS_TOPIC_ARN='${SNS_TOPIC_ARN}'}"
#
#fi

$AWS_CMD lambda update-function-configuration  --function-name rs-$Stage-SNSMessageLambda \
   --environment "Variables={NEWS_ONLINE_LOADER_URL=${dns_name},botoConfig='${botoConfig}',SNS_TOPIC_ARN='${SNS_TOPIC_ARN}'}"

if [[ $? != 0 ]];then
    echo "Error"
    exit 1
fi