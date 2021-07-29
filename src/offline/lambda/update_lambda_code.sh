#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi
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


AWS_ACCOUNT_ID=$($AWS_CMD  sts get-caller-identity  --o text | awk '{print $1}')
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET_BUILD=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=ops-data


lambda_funcs_name=(
 rs-${Stage}-PreCheckLabmda
 rs-${Stage}-S3UtilLabmda
 rs-${Stage}-SNSMessageLambda
 rs-${Stage}-CreateDatasetImportJobLambda
 rs-${Stage}-UpdateSolutionVersionLambda
 rs-${Stage}-UpdateCampaignLambda
)

lambda_funcs_code=(
 precheck-lambda.zip
 s3-util-lambda.zip
 sns-message-lambda.zip
 create-dataset-import-job-lambda.zip
 update-solution-version-lambda.zip
 update-campaign-lambda.zip
)

i=0

for lambda_func_name in ${lambda_funcs_name[@]}; do
  echo "---"
  echo $lambda_func_name
  code_file=${PREFIX}/code/lambda/${lambda_funcs_code[$i]}
  echo $code_file
  $AWS_CMD lambda  update-function-code --function-name ${lambda_func_name} \
  --s3-bucket ${BUCKET_BUILD} \
  --s3-key $code_file >/dev/null
  i=$(( $i+1 ))
done
