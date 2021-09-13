#!/usr/bin/env bash
set -e

dns_name=$(kubectl get svc istio-ingressgateway-news-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo $dns_name
echo "-------"

if [[ $REGION =~ cn.* ]];then
  EC2_IP=$(curl -s 169.254.169.254/latest/meta-data/public-ipv4)
  # dns_name=$(kubectl get svc istio-ingressgateway-news-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
  echo "Please create SSH tunnel on your localhost:"
  echo ""
  echo "ssh -L 8181:$dns_name:22 -i gcr-rs-dev-workshop-ec2-key.pem  ec2-user@$EC2_IP"
  echo ""
  echo "http://localhost:8181"
  echo ""
else
  echo "endpoint: http://$dns_name"
fi