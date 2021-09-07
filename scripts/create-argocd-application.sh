#!/usr/bin/env bash
set -e

# create infra for develop environment
export AWS_PROFILE=default
export REGION=$(aws configure get region)
export EKS_CLUSTER=gcr-rs-dev-application-cluster

echo $AWS_PROFILE
echo $REGION
echo $EKS_CLUSTER

eksctl utils write-kubeconfig --region $REGION --cluster $EKS_CLUSTER --profile $AWS_PROFILE
# 1 login argo cd server
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

endpoint=$(kubectl get svc argocd-server -n argocd -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo user name: admin
echo password: $ARGOCD_PASSWORD
echo endpoint: $endpoint

argocd --insecure login $endpoint:443 --username admin --password $ARGOCD_PASSWORD

# 2 update lambda env
# input=$1

# if [ $input = "cn" ]
# then
#     echo "change to cn region"
#     export AWS_PROFILE=rs-dev-cn-bjs
#     export PROFILE=$AWS_PROFILE
#     # export AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r '.region')
#     export AWS_REGION=cn-north-1
#     export REGION=$AWS_REGION
#     echo $REGION
#      eksctl utils write-kubeconfig --region cn-north-1 --cluster gcr-rs-dev-application-cluster --profile rs-dev-cn-bjs
# fi


echo "update-lambda-env"
./update-lambda-env.sh


# export AWS_PROFILE=default
# export REGION=$(aws configure get region)

# echo $AWS_PROFILE
# echo $REGION
# echo $EKS_CLUSTER

# eksctl utils write-kubeconfig --region $REGION --cluster $EKS_CLUSTER --profile $AWS_PROFILE

# 3 Create argocd application
argocd app create gcr-recommender-system-news-dev --repo https://${ACCESS_TOKEN}@github.com/${GITHUB_USER}/recommender-system-dev-workshop-code.git --path manifests/envs/news-dev --dest-namespace \
rs-news-dev-ns --dest-server https://kubernetes.default.svc --kustomize-image gcr.io/heptio-images/ks-guestbook-demo:0.1

# argocd app create gcr-recommender-system-news-dev --repo https://${ACCESS_TOKEN}@github.com/${GITHUB_USER}/recommender-system-dev-workshop-code.git --path manifests/envs/news-dev --dest-namespace \
# rs-news-dev-ns --dest-server ${APISERVER} --auth-token ${TOKEN} --kustomize-image gcr.io/heptio-images/ks-guestbook-demo:0.1
# eksctl utils write-kubeconfig --region cn-north-1 --cluster gcr-rs-dev-application-cluster --profile rs-dev-cn-bjs

# APISERVER=$(kubectl config view --minify | grep server | cut -f 2- -d ":" | tr -d " ")
# TOKEN=$(kubectl describe secret $SECRET_NAME | grep -E '^token' | cut -f2 -d':' | tr -d " ")

# argocd cluster add rs-online-user@$EKS_CLUSTER.$REGION.eksctl.io

# eksctl utils write-kubeconfig --region $REGION --cluster $EKS_CLUSTER --profile $AWS_PROFILE

# argocd app create gcr-recommender-system-news-dev --repo https://${ACCESS_TOKEN}@github.com/${GITHUB_USER}/recommender-system-dev-workshop-code.git --path manifests/envs/news-dev --dest-namespace \
# rs-news-dev-ns --dest-server $APISERVER --kustomize-image gcr.io/heptio-images/ks-guestbook-demo:0.1

sleep 20

argocd app set gcr-recommender-system-news-dev --sync-policy automated