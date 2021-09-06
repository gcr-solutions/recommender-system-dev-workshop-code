#!/bin/bash

set -e 

StableVersion=$1

AWS_CMD="aws --profile rsops"

todayStr=$(date +"%Y-%m-%d")
bucket=aws-gcr-rs-sol-workshop-ap-northeast-1-common

cdk synth RsRawEC2CdkStack > rs-raw-ec2.yaml
sed -i -e 's/SsmParameterValueawsserviceamiamazonlinuxlatestamzn2ami.*Parameter/SsmParameterValueForImageId/g' ./rs-raw-ec2.yaml

$AWS_CMD s3 cp ./rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/latest/ --acl public-read > /tmp/rs-run.log 2>&1
echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/rs-raw-ec2.yaml"

sed -e "s#rs-dev-workshop-code/latest/main.zip#rs-dev-workshop-code/${todayStr}/main.zip#g" ./rs-raw-ec2.yaml > ./${todayStr}-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./${todayStr}-rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/${todayStr}/rs-raw-ec2.yaml --acl public-read >>/tmp/rs-run.log 2>&1
echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/${todayStr}/rs-raw-ec2.yaml"
rm ${todayStr}-rs-raw-ec2.yaml

sed -e "s#https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/main.zip#https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip#g" > ./github-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./github-rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/github/rs-raw-ec2.yaml --acl public-read >>/tmp/rs-run.log 2>&1
echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/github/rs-raw-ec2.yaml"
rm github-rs-raw-ec2.yaml

rm main.zip > /dev/null 2>&1 || true

wget https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip >> /tmp/rs-run.log 2>&1

$AWS_CMD s3 cp main.zip  s3://${bucket}/rs-dev-workshop-code/latest/ --acl public-read >> /tmp/rs-run.log 2>&1
$AWS_CMD s3 cp main.zip  s3://${bucket}/rs-dev-workshop-code/${todayStr}/ --acl public-read >> /tmp/rs-run.log 2>&1

if [[ $StableVersion == 'v1' ]]; then
    echo "copy to stable_v1"
    sed -i -e 's#rs-dev-workshop-code/latest/main.zip#rs-dev-workshop-code/stable_v1/main.zip#g' ./rs-raw-ec2.yaml
    $AWS_CMD s3 cp main.zip s3://${bucket}/rs-dev-workshop-code/stable_v1/ --acl public-read >> /tmp/rs-run.log 2>&1
    $AWS_CMD s3 cp ./rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/stable_v1/ --acl public-read >> /tmp/rs-run.log 2>&1
    echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/stable_v1/rs-raw-ec2.yaml"
fi 

rm main.zip
rm rs-raw-ec2.yaml-e > /dev/null 2>&1

