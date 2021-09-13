#!/usr/bin/env bash
set -e

curr_dir=$(pwd)

METHOD=$1

if [[ -z $METHOD ]];then
  METHOD='customize'
fi

Stage=$2

if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

SCENARIO=$3

if [[ -z $SCENARIO ]];then
  SCENARIO='news'
fi

if [[ -z $REGION ]];then
  REGION='ap-southeast-1'
fi

AWS_CMD="aws"
if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity  --o text | awk '{print $1}')

if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "METHOD: ${METHOD}"
echo "Stage: ${Stage}"
echo "SCENARIO: ${SCENARIO}"
echo "REGION: ${REGION}"
echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"


BUCKET_BUILD=aws-gcr-rs-sol-${Stage}-${REGION}-${AWS_ACCOUNT_ID}
PREFIX=sample-data-${SCENARIO}

cd ./personalize
./update-ps-config.sh $METHOD $Stage $SCENARIO
cd ..

config_file_path=${curr_dir}/../sample-data/system/ps-config/ps_config.json

if [ $METHOD != "customize" ]
then
  echo "------sync ps_config.json to s3-------"
  aws s3 cp ${config_file_path} s3://${BUCKET_BUILD}/${PREFIX}/system/ps-config/ps_config.json
  aws s3 cp ${config_file_path} s3://${BUCKET_BUILD}/${PREFIX}/notification/ps-result/ps_config.json
  
  echo "------notice online part-------"
  dns_name=$(kubectl get svc istio-ingressgateway-news-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')
  curl -X POST -d '{"message": {"file_type": "ps-result","file_path": "sample-data-news/notification/ps-result/","file_name": ["ps_config.json"]}}' -H "Content-Type:application/json" http://${dns_name}/loader/notice

fi


echo "------update config.yaml file------"
env_config_path=${curr_dir}/../manifests/envs/news-dev/config.yaml
old_method=$(awk -F "\"" '/method/{print $2}' $env_config_path)
echo "change old method: ${old_method} to new method: ${METHOD}"
sed -e "s@$old_method@$METHOD@g" -i "" $env_config_path


echo "------push code to github-------"
git pull
git add ${config_file_path}
git add ${env_config_path}
git commit -m "change method to ${METHOD}"
git push

echo "-------change method successfully-------"



