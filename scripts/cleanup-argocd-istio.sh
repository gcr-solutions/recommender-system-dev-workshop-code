#!/usr/bin/env bash
set -e

cd ../manifests
echo "################ start clean istio and argocd resources ################ "

export EKS_CLUSTER=gcr-rs-dev-workshop-cluster
export EKS_DEV_CLUSTER=gcr-rs-dev-environment-cluster

if [[ $CN_AWS_PROFILE ]];then
  export AWS_PROFILE=$CN_AWS_PROFILE
  export REGION=$(aws configure get region)
  export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text) 
  eksctl utils write-kubeconfig --region $REGION --cluster $EKS_CLUSTER
fi

kubectl delete -f istio-ingress-gateway.yaml

export AWS_PROFILE=default
export REGION=$(aws configure get region)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text) 
eksctl utils write-kubeconfig --region $REGION --cluster $EKS_DEV_CLUSTER

kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

sleep 10

echo "start check istio ingress gateway security group"

if [[ $CN_AWS_PROFILE ]];then
  export AWS_PROFILE=$CN_AWS_PROFILE
  export REGION=$(aws configure get region)
  export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text) 
  eksctl utils write-kubeconfig --region $REGION --cluster $EKS_CLUSTER
fi

i=1
ISTIO_SG_ID=""
while true; do
  ISTIO_SG_ID=$(aws ec2 describe-security-groups --filter Name=tag:kubernetes.io/cluster/gcr-rs-dev-workshop-cluster,Values=owned Name=description,Values=*istio-system/istio-ingressgateway-news-dev* --query "SecurityGroups[*].[GroupId]" --output text)
  if [ "$ISTIO_SG_ID" == "" ]; then
    echo "delete istio security group successfully!"
    break
  else
    echo "wait for istio security group deleted!"
  fi
  sleep 10
done

export AWS_PROFILE=default
export REGION=$(aws configure get region)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text) 
eksctl utils write-kubeconfig --region $REGION --cluster $EKS_DEV_CLUSTER

echo "start check argocd server security group"
j=1
ARGOCD_SG_ID=""
while true; do
  ARGOCD_SG_ID=$(aws ec2 describe-security-groups --filter Name=tag:kubernetes.io/cluster/gcr-rs-dev-environment-cluster,Values=owned Name=description,Values=*argocd/argocd-server* --query "SecurityGroups[*].[GroupId]" --output text)
  if [ "$ARGOCD_SG_ID" == "" ]; then
    echo "delete argocd security group successfully!"
    break
  else
    echo "wait for argocd server security group deleted!"
  fi
  sleep 10
done

echo $ISTIO_SG_ID
echo $ARGOCD_SG_ID

if [[ $CN_AWS_PROFILE ]];then
  export AWS_PROFILE=$CN_AWS_PROFILE
  export REGION=$(aws configure get region)
  export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text) 
  eksctl utils write-kubeconfig --region $REGION --cluster $EKS_CLUSTER
fi

if [ "$ISTIO_SG_ID" != "" ]; then
  echo "delete istio security group!"
  aws ec2 delete-security-group --group-id $ISTIO_SG_ID
fi

export AWS_PROFILE=default
export REGION=$(aws configure get region)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text) 
eksctl utils write-kubeconfig --region $REGION --cluster $EKS_DEV_CLUSTER

if [ "$ARGOCD_SG_ID" != "" ]; then
  echo "delete argocd security group!"
  aws ec2 delete-security-group --group-id $ARGOCD_SG_ID
fi

cd ../scripts
