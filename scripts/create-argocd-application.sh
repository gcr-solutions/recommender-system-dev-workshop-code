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
USER_NAME="gcr-rs-codecommit-user-at-002224604296"
PASS_WRD="nuZYIyXHfA2W+qwoLxto4Q3Q1oHwMDsnh+ebquz9Y9E="
REPO = "https://git-codecommit.ap-southeast-1.amazonaws.com/v1/repos/recommender-system-dev-workshop-code"
argocd repo add $REPO --username $USER_NAME --password $PASS_WRD --insecure-skip-server-verification

argocd app create gcr-recommender-system-news-dev --repo $REPO --path manifests/envs/news-dev --dest-namespace \
rs-news-dev-ns --dest-server https://kubernetes.default.svc --kustomize-image gcr.io/heptio-images/ks-guestbook-demo:0.1

sleep 20

argocd app set gcr-recommender-system-news-dev --sync-policy automated