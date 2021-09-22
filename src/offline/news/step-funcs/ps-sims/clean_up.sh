#!/usr/bin/env bash
set -e

echo "run $0 ..."
pwd

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

if [[ -z $REGION ]];then
    REGION='ap-northeast-1'
fi

echo "AWS_CMD: $AWS_CMD"
echo "REGION: $REGION"


AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

NamePrefix=rs-news-ps-sims-$Stage

all_stepfuncs=(
infra
steps
dashboard
inverted-list
batch-update
user-new
item-new
train-model
overall
prepare-ps-action
prepare-ps-item
prepare-ps-user
train-ps-model
item-sims-update
)

for name in ${all_stepfuncs[@]};
do
    STACK_NAME=${NamePrefix}-${name}-stack
    echo "----"
    echo "Clean STACK_NAME: ${STACK_NAME}"
    $AWS_CMD cloudformation delete-stack --region ${REGION} --stack-name ${STACK_NAME}
done

