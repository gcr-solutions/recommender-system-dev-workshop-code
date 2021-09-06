#!/bin/bash

set -e 

git pull

ReleaseVersion=$1

AWS_CMD="aws --profile rsops"

todayStr=$(date +"%Y-%m-%d")
bucket=aws-gcr-rs-sol-workshop-ap-northeast-1-common

cdk synth RsRawEC2CdkStack > rs-raw-ec2.yaml
sed -i -e 's/SsmParameterValueawsserviceamiamazonlinuxlatestamzn2ami.*Parameter/SsmParameterValueForImageId/g' ./rs-raw-ec2.yaml

$AWS_CMD s3 cp ./rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/latest/ --acl public-read 

sed -e "s#rs-dev-workshop-code/latest/main.zip#rs-dev-workshop-code/${todayStr}/main.zip#g" ./rs-raw-ec2.yaml > ./${todayStr}-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./${todayStr}-rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/${todayStr}/rs-raw-ec2.yaml --acl public-read 
rm ${todayStr}-rs-raw-ec2.yaml

sed -e "s#${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/main.zip#github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip#g" ./rs-raw-ec2.yaml > ./github-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./github-rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/github/rs-raw-ec2.yaml --acl public-read 
rm github-rs-raw-ec2.yaml

rm main.zip > /dev/null 2>&1 || true

wget https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip || {
   echo "fail to download recommender-system-dev-workshop-code"
   exit 1
 }


$AWS_CMD s3 cp main.zip  s3://${bucket}/rs-dev-workshop-code/latest/ --acl public-read
$AWS_CMD s3 cp main.zip  s3://${bucket}/rs-dev-workshop-code/${todayStr}/ --acl public-read

if [[ $ReleaseVersion =~ v.* ]]; then
    echo "release $ReleaseVersion"
    sed -i -e "s#rs-dev-workshop-code/latest/main.zip#rs-dev-workshop-code/release/$ReleaseVersion/main.zip#g" ./rs-raw-ec2.yaml
    $AWS_CMD s3 cp main.zip s3://${bucket}/rs-dev-workshop-code/release/$ReleaseVersion/ --acl public-read
    $AWS_CMD s3 cp ./rs-raw-ec2.yaml s3://${bucket}/rs-dev-workshop-code/release/$ReleaseVersion/ --acl public-read
    rm -rf ./doc/ > /dev/null 2>&1  || true
    mkdir ./doc/
    cd ./doc/
    wget https://github.com/gcr-solutions/recommender-system-dev-workshop/archive/refs/heads/main.zip || {
       echo "fail to download recommender-system-dev-workshop"
       exit 1
    }
    $AWS_CMD s3 cp ./main.zip s3://${bucket}/rs-dev-workshop-code/release/$ReleaseVersion/doc/
    cd ..
    rm -rf ./doc/
fi

rm main.zip
rm rs-raw-ec2.yaml-e > /dev/null 2>&1  || true

echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/rs-raw-ec2.yaml"
echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/${todayStr}/rs-raw-ec2.yaml"
echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/github/rs-raw-ec2.yaml"

if [[ $ReleaseVersion =~ v.* ]]; then
      echo "https://${bucket}.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/release/$ReleaseVersion/rs-raw-ec2.yaml"
fi
