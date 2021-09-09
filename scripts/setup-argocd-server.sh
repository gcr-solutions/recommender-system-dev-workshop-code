#!/usr/bin/env bash
set -e

export EKS_CLUSTER=gcr-rs-dev-application-cluster

echo $EKS_CLUSTER

# 1 setup argocd server
kubectl create namespace argocd || true

install_link="https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/eks/argocd/install.yaml"
if [[ $REGION =~ cn.* ]];then
  install_link="https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/argocd/install.yaml"
fi

echo "1. $install_link"
kubectl apply -n argocd -f $install_link

sleep 10

kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# 2 install argocd cli
#VERSION=$(curl --silent "https://api.github.com/repos/argoproj/argo-cd/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')

install_link="https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/eks/argocd/argocd-linux-amd64-v2.1.2"
if [[ $REGION =~ cn.* ]];then
  install_link="https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/eks/argocd/argocd-linux-amd64-v2.1.2"
fi

echo "2. $install_link"

rm -rf /usr/local/bin/argocd > /dev/null 2>&1 || true

sudo curl -sSL -o /usr/local/bin/argocd $install_link

sudo chmod +x /usr/local/bin/argocd

sleep 30

# 3 get admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

dns_name=$(kubectl get svc argocd-server -n argocd -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo user name: admin
echo password: $ARGOCD_PASSWORD
echo endpoint: http://$dns_name

