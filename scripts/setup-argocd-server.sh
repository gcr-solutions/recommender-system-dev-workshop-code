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

#Open argocd elb 22 port for China regions
if [[ $REGION =~ ^cn.* ]];then
  echo "open 22 port for china regions"

  while true; do
     sleep 60
     ELB_NAME=$(aws resourcegroupstaggingapi get-resources --tag-filters Key=kubernetes.io/service-name,Values=argocd/argocd-server  | jq -r '.ResourceTagMappingList[].ResourceARN' | cut -d'/' -f 2)

     if [[ -n $ELB_NAME ]];then
         echo load balance name: $ELB_NAME
         break
     else
         echo "wait for load balance ready ..."
     fi
  done

  INSTANCE_PORT=$(kubectl get svc argocd-server -n argocd -o=jsonpath='{.spec.ports[?(@.port==80)].nodePort}')
  echo instance port: $INSTANCE_PORT

  aws elb create-load-balancer-listeners --load-balancer-name $ELB_NAME --listeners "Protocol=TCP,LoadBalancerPort=22,InstanceProtocol=TCP,InstancePort=$INSTANCE_PORT"

  ELB_SG_ID=$(aws elb describe-load-balancers --load-balancer-names $ELB_NAME | jq -r '.LoadBalancerDescriptions[].SecurityGroups[]')
  echo load balance security group id: $ELB_SG_ID

  aws ec2 authorize-security-group-ingress --group-id $ELB_SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
fi

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


# 3 get admin password
echo "get admin password"
sleep 30
while true; do
    ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
    if [[ -n $ARGOCD_PASSWORD ]]; then
      break
    fi
    echo "wait argocd-initial-admin-secret ..."
    sleep 30
done

while true; do
  dns_name=$(kubectl get svc argocd-server -n argocd -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
  if [[ -n $dns_name ]];then
    break
  fi
  echo "wait argocd-server ready ..."
  sleep 30
done

echo $dns_name

echo "-------"

if [[ $REGION =~ cn.* ]];then
  EC2_IP=$(curl -s 169.254.169.254/latest/meta-data/public-ipv4)
  #LB_DNS=$(kubectl get svc argocd-server -n argocd -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
  #echo "argocd-server: $LB_DNS"
  echo "Please create SSH tunnel on your localhost:"
  echo ""
  echo "ssh -L 8182:$dns_name:22 -i gcr-rs-dev-workshop-ec2-key.pem  ec2-user@$EC2_IP"
  echo ""
  echo "endpoint: http://localhost:8182"
  echo "user name: admin"
  echo "password: $ARGOCD_PASSWORD"
  echo ""
else
  echo user name: admin
  echo password: $ARGOCD_PASSWORD
  echo endpoint: http://$dns_name
fi

echo "Please stop printing the log by typing CONTROL+C "
