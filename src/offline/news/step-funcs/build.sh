#!/usr/bin/env bash


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


AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET=aws-gcr-rs-sol-$Stage-${REGION}-${AWS_ACCOUNT_ID}
S3Prefix=sample-data-news

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

ps_complete_stepfuncs=(
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

ps_rank_stepfuncs=(
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

ps_sims_stepfuncs=(
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

if [[ "$METHOD" == "customize" ]];then
  NamePrefix=rs-news-customize-$Stage
  PARAMETER_OVERRIDES="Stage=$Stage NamePrefix=${NamePrefix} Bucket=$BUCKET S3Prefix=$S3Prefix"
  echo PARAMETER_OVERRIDES:$PARAMETER_OVERRIDES

  for name in ${customize_stepfuncs[@]};
  do
      STACK_NAME=${NamePrefix}-${name}-stack
      template_file=${name}-template.yaml
      echo "----"
      echo "STACK_NAME: ${STACK_NAME}"
      echo "template_file: ${template_file}"

      $AWS_CMD  cloudformation deploy --region ${REGION} \
      --template-file customize/${template_file} --stack-name ${STACK_NAME} \
      --parameter-overrides ${PARAMETER_OVERRIDES} \
      --capabilities CAPABILITY_NAMED_IAM \
      --no-fail-on-empty-changeset

       StackStatus=$($AWS_CMD  cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
       echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

       if [[ $? -ne 0 ]]; then
           echo "error!!!  ${StackStatus}"
           exit 1
       fi

      rm tmp_*.yaml > /dev/null 2>&1  || true
  done
elif [ $METHOD == "ps-complete" ]; then
  NamePrefix=rs-news-ps-complete-$Stage
  PARAMETER_OVERRIDES="Stage=$Stage NamePrefix=${NamePrefix} Bucket=$BUCKET S3Prefix=$S3Prefix"
  echo PARAMETER_OVERRIDES:$PARAMETER_OVERRIDES

  for name in ${ps_complete_stepfuncs[@]};
  do
      STACK_NAME=${NamePrefix}-${name}-stack
      template_file=${name}-template.yaml
      echo "----"
      echo "STACK_NAME: ${STACK_NAME}"
      echo "template_file: ${template_file}"

      $AWS_CMD  cloudformation deploy --region ${REGION} \
      --template-file ps-complete/${template_file} --stack-name ${STACK_NAME} \
      --parameter-overrides ${PARAMETER_OVERRIDES} \
      --capabilities CAPABILITY_NAMED_IAM \
      --no-fail-on-empty-changeset

       StackStatus=$($AWS_CMD  cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
       echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

       if [[ $? -ne 0 ]]; then
           echo "error!!!  ${StackStatus}"
           exit 1
       fi

      rm tmp_*.yaml > /dev/null 2>&1  || true
  done
elif [ $METHOD == "ps-rank" ]; then
  NamePrefix=rs-news-ps-rank-$Stage
  PARAMETER_OVERRIDES="Stage=$Stage NamePrefix=${NamePrefix} Bucket=$BUCKET S3Prefix=$S3Prefix"
  echo PARAMETER_OVERRIDES:$PARAMETER_OVERRIDES

  for name in ${ps_rank_stepfuncs[@]};
  do
      STACK_NAME=${NamePrefix}-${name}-stack
      template_file=${name}-template.yaml
      echo "----"
      echo "STACK_NAME: ${STACK_NAME}"
      echo "template_file: ${template_file}"

      $AWS_CMD  cloudformation deploy --region ${REGION} \
      --template-file ps-rank/${template_file} --stack-name ${STACK_NAME} \
      --parameter-overrides ${PARAMETER_OVERRIDES} \
      --capabilities CAPABILITY_NAMED_IAM \
      --no-fail-on-empty-changeset

       StackStatus=$($AWS_CMD  cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
       echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

       if [[ $? -ne 0 ]]; then
           echo "error!!!  ${StackStatus}"
           exit 1
       fi

      rm tmp_*.yaml > /dev/null 2>&1  || true
  done
elif [ $METHOD == "ps-sims" ]; then
  NamePrefix=rs-news-ps-sims-$Stage
  PARAMETER_OVERRIDES="Stage=$Stage NamePrefix=${NamePrefix} Bucket=$BUCKET S3Prefix=$S3Prefix"
  echo PARAMETER_OVERRIDES:$PARAMETER_OVERRIDES

  for name in ${ps_sims_stepfuncs[@]};
  do
      STACK_NAME=${NamePrefix}-${name}-stack
      template_file=${name}-template.yaml
      echo "----"
      echo "STACK_NAME: ${STACK_NAME}"
      echo "template_file: ${template_file}"

      $AWS_CMD  cloudformation deploy --region ${REGION} \
      --template-file ps-sims/${template_file} --stack-name ${STACK_NAME} \
      --parameter-overrides ${PARAMETER_OVERRIDES} \
      --capabilities CAPABILITY_NAMED_IAM \
      --no-fail-on-empty-changeset

       StackStatus=$($AWS_CMD  cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
       echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

       if [[ $? -ne 0 ]]; then
           echo "error!!!  ${StackStatus}"
           exit 1
       fi

      rm tmp_*.yaml > /dev/null 2>&1  || true
  done
elif [ $METHOD == "all" ]; then
  method_list=(
    "customize"
    "ps-complete"
    "ps-rank"
    "ps-sims"
  )
  stepfuncs_list=(
    "customize_stepfuncs"
    "ps_complete_stepfuncs"
    "ps_rank_stepfuncs"
    "ps_sims_stepfuncs"
  )
  for i in 0 1 2 3;
  do
    NamePrefix=rs-news-${method_list[i]}-$Stage
    PARAMETER_OVERRIDES="Stage=$Stage NamePrefix=${NamePrefix} Bucket=$BUCKET S3Prefix=$S3Prefix"
    echo PARAMETER_OVERRIDES:$PARAMETER_OVERRIDES

    stepfuncs_name=${stepfuncs_list[i]}
    for name in ${${stepfuncs_name}[@]};
    do
        STACK_NAME=${NamePrefix}-${name}-stack
        template_file=${name}-template.yaml
        echo "----"
        echo "STACK_NAME: ${STACK_NAME}"
        echo "template_file: ${template_file}"

        $AWS_CMD  cloudformation deploy --region ${REGION} \
        --template-file ${method_list[i]}/${template_file} --stack-name ${STACK_NAME} \
        --parameter-overrides ${PARAMETER_OVERRIDES} \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset

         StackStatus=$($AWS_CMD  cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
         echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

         if [[ $? -ne 0 ]]; then
             echo "error!!!  ${StackStatus}"
             exit 1
         fi

        rm tmp_*.yaml > /dev/null 2>&1  || true
    done
  done
fi


