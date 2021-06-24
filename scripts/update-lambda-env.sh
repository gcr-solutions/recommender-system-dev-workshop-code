#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

echo "Stage=$Stage"
AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

if [[ -n $AWS_DEFAULT_REGION ]];then
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
echo "dns_name: $dns_name"

botoConfig='{"user_agent_extra": "AwsSolution/SO8010/0.1.0"}'
SNS_TOPIC_ARN="arn:aws:sns:${REGION}:${account_id}:rs-$Stage-offline-sns"
echo $SNS_TOPIC_ARN

# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| join (",")'
# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| .[]'

$AWS_CMD lambda   update-function-configuration  --function-name rs-$Stage-SNSMessageLambda \
--environment "Variables={NEWS_ONLINE_LOADER_URL=${dns_name},botoConfig='${botoConfig}',SNS_TOPIC_ARN='${SNS_TOPIC_ARN}'}" >/dev/null


