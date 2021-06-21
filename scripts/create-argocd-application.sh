#!/usr/bin/env bash
set -e

# 1 login argo cd server
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

endpoint=$(kubectl get svc argocd-server -n argocd -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo user name: admin
echo password: $ARGOCD_PASSWORD
echo endpoint: $endpoint

argocd --insecure login $endpoint:443 --username admin --password $ARGOCD_PASSWORD

# 2 update lambda env

echo "update-lambda-env"
./update-lambda-env.sh

# 3 Create argocd application
argocd app create gcr-recommender-system-news-dev --repo https://github.com/__GITHUB_USER_NAME__/recommender-system-dev-workshop-code.git --path manifests/envs/news-dev --dest-namespace \
rs-news-dev-ns --dest-server https://kubernetes.default.svc --kustomize-image gcr.io/heptio-images/ks-guestbook-demo:0.1

sleep 20

argocd app set gcr-recommender-system-news-dev --sync-policy automated