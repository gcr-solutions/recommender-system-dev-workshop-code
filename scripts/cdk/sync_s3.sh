#!/bin/bash

set -e 

StableVersion=$1

AWS_CMD="aws --profile rsops"

cdk synth RsRawEC2CdkStack > rs-raw-ec2.yaml
sed -i -e 's/SsmParameterValueawsserviceamiamazonlinuxlatestamzn2ami.*Parameter/SsmParameterValueForImageId/g' ./rs-raw-ec2.yaml
$AWS_CMD s3 cp ./rs-raw-ec2.yaml s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/rs-dev-workshop-code/latest/ --acl public-read


rm main.zip > /dev/null 2>&1 || true
echo 'https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/rs-raw-ec2.yaml'

wget https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip

$AWS_CMD s3 cp main.zip  s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/rs-dev-workshop-code/latest/ --acl public-read
$AWS_CMD s3 cp main.zip  s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/rs-dev-workshop-code/$(date +"%Y-%m-%d")/ --acl public-read

if [[ $StableVersion == 'v1' ]]; then
    echo "copy to stable_v1"
    sed -i -e 's#rs-dev-workshop-code/latest/main.zip#rs-dev-workshop-code/stable_v1/main.zip#g' ./rs-raw-ec2.yaml
    $AWS_CMD s3 cp main.zip s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/rs-dev-workshop-code/stable_v1/ --acl public-read
    $AWS_CMD s3 cp ./rs-raw-ec2.yaml s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/rs-dev-workshop-code/stable_v1/ --acl public-read
    echo 'https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/stable_v1/rs-raw-ec2.yaml'
fi 

rm main.zip

