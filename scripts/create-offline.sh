#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

Stage=$1
if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

if [[ -z $REGION ]]; then
  REGION='ap-northeast-1'
fi

echo "Stage=$Stage"
echo "REGION=$REGION"

#if [[ -z $GITHUB_USER ]]; then
#     echo "error!!! can not get your GITHUB_USER, please set it use 'export GITHUB_USER=<your github username>'"
#     exit 1
#fi
#echo "GITHUB_USER: ${GITHUB_USER}"

AWS_CMD="aws --profile default"

#if [[ -n $AWS_PROFILE ]]; then
#  export PROFILE=$AWS_PROFILE
#fi

if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi
echo "AWS_CMD=$AWS_CMD"

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)

echo "AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}"


if [[ -z $RS_SCENARIO  ]];then
    RS_SCENARIO=news
fi

echo "RS_SCENARIO: $RS_SCENARIO"


echo "========= Create S3 Bucket =============="
BUCKET_BUILD=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=sample-data-$RS_SCENARIO


echo "BUCKET_BUILD=${BUCKET_BUILD}"

$AWS_CMD s3api --region $REGION create-bucket --bucket ${BUCKET_BUILD}  \
--create-bucket-configuration LocationConstraint=$REGION >/dev/null 2>&1 || true

$AWS_CMD  s3 mb s3://${BUCKET_BUILD}  >/dev/null 2>&1 || true

sleep 3
echo "0. ========= Create codebuild Role =============="
cd ${curr_dir}/codebuild
./create-codebuild-role.sh $Stage

echo "1. ========= Create codebuild =============="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline-codecommit.sh $Stage

echo "2. ========= sync sample data to S3 ($RS_SCENARIO) =============="
cd ${curr_dir}/../sample-data

if [[ $RS_SCENARIO == 'news' ]];then
   ./sync_data_to_s3.sh $Stage
elif [[ $RS_SCENARIO == 'movie' ]];then
   ./sync_moive_data_to_s3.sh $Stage
fi


#echo "3. ========= Build lambda =============="
#cd ${curr_dir}/../src/offline/lambda
#./build.sh $Stage
#
#echo "4. ========= Build stepfuncs =============="
#cd ${curr_dir}/../src/offline/news/step-funcs
#./build.sh $Stage

echo "You can run your step-funcs with below input"
echo '{
  "Bucket": "aws-gcr-rs-sol-'${Stage}'-'${REGION}'-'${AWS_ACCOUNT_ID}'",
  "S3Prefix": '"$PREFIX"',
  "change_type": "ITEM|BATCH|USER|MODEL"
}'
echo ""
echo "Offline resources are created successfully"

if [[  -z $NOT_PRINTING_CONTROL_C ]];then
   echo "Please stop printing the log by typing CONTROL+C "
fi

