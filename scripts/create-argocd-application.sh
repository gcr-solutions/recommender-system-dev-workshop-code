#!/usr/bin/env bash
set -e

# 1 login argo cd server
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

endpoint=$(kubectl get svc argocd-server -n argocd -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo user name: admin
echo password: $ARGOCD_PASSWORD
echo endpoint: $endpoint

echo "argocd login [$REGION]..."
if [[ $REGION =~ cn.* ]];then
   argocd --insecure login $endpoint:22 --username admin --password $ARGOCD_PASSWORD
else
   argocd --insecure login $endpoint:443 --username admin --password $ARGOCD_PASSWORD
fi

# 2 update lambda env

echo "update-lambda-env"
./update-lambda-env.sh

# 3 Create argocd application
CODE_COMMIT_USER=gcr-rs-codecommit-user_$REGION
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text)

if $(aws iam get-user --user-name ${CODE_COMMIT_USER} >/dev/null 2>&1 );then
  echo delete $CODE_COMMIT_USER
  aws iam list-attached-user-policies --user-name $CODE_COMMIT_USER
  POLICY_ARNS=$(aws iam list-attached-user-policies --user-name $CODE_COMMIT_USER | jq '.[][].PolicyArn' -r)
  for POLICY_ARN in $(echo $POLICY_ARNS); do
    aws iam detach-user-policy --user-name $CODE_COMMIT_USER --policy-arn $POLICY_ARN
  done
  SER_ID=$(aws iam list-service-specific-credentials --user-name $CODE_COMMIT_USER --service-name codecommit.amazonaws.com | jq -r '.[][].ServiceSpecificCredentialId')
  aws iam delete-service-specific-credential --user-name $CODE_COMMIT_USER --service-specific-credential-id $SER_ID
  aws iam delete-user --user-name $CODE_COMMIT_USER
fi

echo "aws iam create-user --user-name $CODE_COMMIT_USER"
aws iam create-user --user-name $CODE_COMMIT_USER
if [ $REGION = "cn-north-1" ] || [ $REGION = "cn-northwest-1" ]
then
  aws iam attach-user-policy --policy-arn arn:aws-cn:iam::aws:policy/AWSCodeCommitFullAccess --user-name $CODE_COMMIT_USER
else
  aws iam attach-user-policy --policy-arn arn:aws:iam::aws:policy/AWSCodeCommitFullAccess --user-name $CODE_COMMIT_USER
fi

echo "create-service-specific-credential --user-name $CODE_COMMIT_USER ..."
CODE_COMMIT_PASSWORD=$(aws iam create-service-specific-credential --user-name $CODE_COMMIT_USER --service-name codecommit.amazonaws.com --query "ServiceSpecificCredential.ServicePassword" --output text)
echo "CODE_COMMIT_PASSWORD: $CODE_COMMIT_PASSWORD"
REPO_USER=$CODE_COMMIT_USER-at-$AWS_ACCOUNT_ID
echo "REPO_USER: $REPO_USER"
REPO_URL=$(aws codecommit get-repository --repository-name $APP_CONF_REPO --query "repositoryMetadata.cloneUrlHttp" --output text)
echo "REPO_URL: $REPO_URL"

sleep 40

echo "argocd repo add $REPO_URL ..."
argocd repo add $REPO_URL --username $REPO_USER --password $CODE_COMMIT_PASSWORD --insecure-skip-server-verification --upsert

echo "argocd app create gcr-recommender-system-news-dev ..."
argocd app create gcr-recommender-system-news-dev --repo $REPO_URL --path manifests/envs/news-dev --dest-namespace \
rs-news-dev-ns --dest-server https://kubernetes.default.svc --kustomize-image gcr.io/heptio-images/ks-guestbook-demo:0.1 \
--upsert

sleep 20
echo "app set gcr-recommender-system-news-dev ..."
argocd app set gcr-recommender-system-news-dev --sync-policy automated

echo "Please stop printing the log by typing CONTROL+C "
