#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
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

elb_names=($($AWS_CMD elb describe-load-balancers --output text | grep LOADBALANCERDESCRIPTIONS |  awk '{print $6 }'))

echo "find $#elb_names elbs"

ingressgateway_elb=''
for elb in ${elb_names[@]};
do
  echo "check elb $elb ..."
  $AWS_CMD elb describe-tags --load-balancer-name $elb --output text  | grep 'istio-ingressgateway'
  if [[ $? -eq '0' ]];then
     echo "find ingressgateway $elb"
     ingressgateway_elb=$elb
     break
  fi
done

echo "ingressgateway_elb: $ingressgateway_elb"

if [[ -z $ingressgateway_elb ]];then
  echo "Error: cannot find istio ingress gateway"
  exit 1
fi

dns_name=$($AWS_CMD elb describe-load-balancers --load-balancer-name $ingressgateway_elb --output text | grep LOADBALANCERDESCRIPTIONS | awk '{print $2 }')

echo "dns_name: $dns_name"

loader_url="http://$dns_name/loader/notice"
echo $loader_url

botoConfig='{"user_agent_extra": "AwsSolution/SO8010/0.1.0"}'
SNS_TOPIC_ARN="arn:aws:sns:${REGION}:${account_id}:rs-$Stage-offline-sns"
echo $SNS_TOPIC_ARN

# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| join (",")'
# aws --profile rsops lambda get-function-configuration  --function-name rs-dev-SNSMessageLambda | jq .Environment.Variables | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")| .[]'

$AWS_CMD lambda   update-function-configuration  --function-name rs-$Stage-SNSMessageLambda \
--environment "Variables={ONLINE_LOADER_URL=${loader_url},botoConfig='${botoConfig}',SNS_TOPIC_ARN='${SNS_TOPIC_ARN}'}" >/dev/null


