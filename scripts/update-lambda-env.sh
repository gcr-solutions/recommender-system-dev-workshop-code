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
if [[ -n $CN_AWS_PROFILE ]]; then
  PROFILE=$CN_AWS_PROFILE
  CN_REGION=$(aws --profile $CN_AWS_PROFILE configure get region)
  if [[ -z $CN_REGION ]];then
      CN_REGION='cn-north-1'
  fi
  REGION=$CN_REGION
  echo "You set Env: CN_AWS_PROFILE=$CN_AWS_PROFILE, switch to REGION: $REGION"
  eksctl utils write-kubeconfig --region ${REGION} --cluster gcr-rs-dev-workshop-cluster --profile ${CN_AWS_PROFILE}
  if [[ $? != 0 ]];then
    echo "Error"
    exit 1
  fi
fi

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

botoConfig='{"user_agent_extra": "AwsSolution/SO8010/0.1.0"}'
SNS_TOPIC_ARN="arn:aws:sns:${REGION}:${account_id}:rs-$Stage-offline-sns"
echo $SNS_TOPIC_ARN

# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| join (",")'
# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| .[]'

$AWS_CMD lambda update-function-configuration  --function-name rs-$Stage-SNSMessageLambda \
--environment "Variables={NEWS_ONLINE_LOADER_URL=${dns_name},botoConfig='${botoConfig}',SNS_TOPIC_ARN='${SNS_TOPIC_ARN}'}" >/dev/null
if [[ $? != 0 ]];then
    echo "Error"
    exit 1
fi


