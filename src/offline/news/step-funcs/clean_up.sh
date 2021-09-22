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

METHOD=$2
if [[ -z $METHOD ]];then
  METHOD='customize'
fi

echo "METHOD=$METHOD"

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

NamePrefix=rs-news-customize-$Stage

customize_stepfuncs=(
steps
dashboard
batch-update
user-new
item-new
#item-new-assembled
train-model
overall
)

ps-complete_stepfuncs=(
prepare-action
prepare-item
prepare-user
batch-update
item-new
user-new
train-model
train-model-ps
overall
#dashboard
steps
)

ps-rank_stepfuncs=(
infra
steps
dashboard
inverted-list
batch-update
user-new
item-new
train-model
overall
prepare-action
prepare-item
prepare-user
train-model-ps
)

ps-sims_stepfuncs=(
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


method_list=(
    "customize"
    "ps-complete"
    "ps-rank"
    "ps-sims"
)
for method in ${method_list[@]};
do
  NamePrefix=rs-news-${method}-$Stage
  PARAMETER_OVERRIDES="Stage=$Stage NamePrefix=${NamePrefix} Bucket=$BUCKET S3Prefix=$S3Prefix"
  echo PARAMETER_OVERRIDES:$PARAMETER_OVERRIDES

  for name in ${${method}_stepfuncs[@]};
  do
    STACK_NAME=${NamePrefix}-${name}-stack
    echo "----"
    echo "Clean STACK_NAME: ${STACK_NAME}"
    $AWS_CMD cloudformation delete-stack --region ${REGION} --stack-name ${STACK_NAME} >/dev/null 2>&1 || true
  done
done

