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

if [[ -n $AWS_DEFAULT_REGION && -z $REGION ]];then
  REGION=$AWS_DEFAULT_REGION
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

echo "AWS_CMD: $AWS_CMD"
echo "REGION: $REGION"

AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity --query Account --output text)

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"

if [[ -z $RS_SCENARIO  ]];then
    RS_SCENARIO=news
fi

echo "RS_SCENARIO: $RS_SCENARIO"

dns_name=$(kubectl get svc istio-ingressgateway-news-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
if [[ $? != 0 ]];then
    echo "Error"
    exit 1
fi

echo "dns_name($RS_SCENARIO): $dns_name"


BUCKET=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
S3Prefix=ops-data

PARAMETER_OVERRIDES="Bucket=$BUCKET S3Prefix=$S3Prefix Stage=$Stage"

if [[ $RS_SCENARIO == 'news' ]];then
  PARAMETER_OVERRIDES="$PARAMETER_OVERRIDES NewsOnlineLoaderURL=$dns_name"
fi

if [[ $RS_SCENARIO == 'movie' ]];then
  PARAMETER_OVERRIDES="$PARAMETER_OVERRIDES MovieOnlineLoaderURL=$dns_name"
fi

echo ""
echo "PARAMETER_OVERRIDES: $PARAMETER_OVERRIDES"
echo ""

STACK_NAME=rs-$Stage-lambda-stack
echo "STACK_NAME: ${STACK_NAME}"
echo "$AWS_CMD cloudformation deploy --region ${REGION} \
--template-file ./template.yaml --stack-name ${STACK_NAME} \
--parameter-overrides ${PARAMETER_OVERRIDES} \
--capabilities CAPABILITY_NAMED_IAM"

$AWS_CMD  cloudformation deploy --region ${REGION} \
--template-file ./template.yaml --stack-name ${STACK_NAME} \
--parameter-overrides ${PARAMETER_OVERRIDES} \
--capabilities CAPABILITY_NAMED_IAM \
--no-fail-on-empty-changeset

if [[ $? != 0 ]];then
    echo "Error"
    exit 1
fi