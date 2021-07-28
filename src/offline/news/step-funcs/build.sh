#!/usr/bin/env bash


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


AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET=aws-gcr-rs-sol-$Stage-${REGION}-${AWS_ACCOUNT_ID}
S3Prefix=sample-data-news

PARAMETER_OVERRIDES="Bucket=$BUCKET S3Prefix=$S3Prefix Stage=$Stage"
echo PARAMETER_OVERRIDES:$PARAMETER_OVERRIDES

all_stepfuncs=(
steps
dashboard
batch-update
user-new
item-new
#item-new-assembled
train-model
overall
)

for name in ${all_stepfuncs[@]};
do

    STACK_NAME=rs-$Stage-news-${name}-stack
    template_file=${name}-template.yaml
    echo "----"
    echo "STACK_NAME: ${STACK_NAME}"
    echo "template_file: ${template_file}"
    if [[ $name =~ ^(steps|item-new-assembled)$ && $REGION =~ ^cn.* ]]; then
      org_template_file=${template_file}
      sed 's#.amazonaws.com#.amazonaws.com.cn#g' ${template_file} > tmp_1_${org_template_file}
      sed 's#522244679887.dkr.ecr.ap-northeast-1#'${AWS_ACCOUNT_ID}'.dkr.ecr.'${REGION}'#g' tmp_1_${org_template_file}  > tmp_2_${org_template_file}
      template_file=tmp_2_${org_template_file}
      echo "changed template_file: ${template_file}"
    fi

    if [[ $name =~ ^(steps)$ && ! ($REGION =~ ^(ap-northeast-1|cn.*)$) ]]; then
        org_template_file_2=$template_file
        sed 's#522244679887.dkr.ecr.ap-northeast-1#'${AWS_ACCOUNT_ID}'.dkr.ecr.'${REGION}'#g' ${org_template_file_2}  > tmp_3_${org_template_file_2}
        template_file=tmp_3_${org_template_file_2}
    fi

    $AWS_CMD  cloudformation deploy --region ${REGION} \
    --template-file ${template_file} --stack-name ${STACK_NAME} \
    --parameter-overrides ${PARAMETER_OVERRIDES} \
    --capabilities CAPABILITY_NAMED_IAM


     StackStatus=$($AWS_CMD  cloudformation  describe-stacks --region ${REGION} --stack-name ${STACK_NAME} --output table | grep StackStatus)
     echo ${StackStatus} |  egrep "(CREATE_COMPLETE)|(UPDATE_COMPLETE)" > /dev/null

     if [[ $? -ne 0 ]]; then
         echo "error!!!  ${StackStatus}"
         exit 1
     fi

    rm tmp_*.yaml > /dev/null 2>&1  || true

done

