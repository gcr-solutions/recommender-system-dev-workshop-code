#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
pwd

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
AWS_REGION=$REGION


AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')
echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"

BUCKET_BUILD=aws-gcr-rs-sol-$Stage-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=ops-data

echo "BUCKET_BUILD=${BUCKET_BUILD}"
echo "Create S3 Bucket: ${BUCKET_BUILD} if not exist"

lambda_funcs=(
  precheck-lambda
  s3-util-lambda
  sns-message-lambda
  create-dataset-import-job-lambda
  update-solution-version-lambda
  update-campaign-lambda
)

rm -rf deploy >/dev/null 2>&1

mkdir deploy/
cd deploy/

pip install --target ./package requests >/dev/null

if [[ $? -ne 0 ]]; then
    echo "error!!!"
    exit 1
fi

for lambda_func in ${lambda_funcs[@]}; do
  cp ../${lambda_func}.py .
  cd package
  zip -r ../${lambda_func}.zip . >/dev/null
  cd ..
  zip -g ${lambda_func}.zip ./${lambda_func}.py

  if [[ $? -ne 0 ]]; then
    echo "error!!!"
    exit 1
  fi
  rm ./${lambda_func}.py
done

rm -rf package


$AWS_CMD s3 sync . s3://${BUCKET_BUILD}/${PREFIX}/code/lambda/
if [[ $? -ne 0 ]]; then
    echo "error!!!"
    exit 1
fi
cd ..
#rm -rf deploy