#!/bin/bash

set -e 

git pull

ReleaseVersion=$1

if [[ -n $ReleaseVersion ]];then
  if git tag -a $ReleaseVersion -m "new release $ReleaseVersion"; then
        git push origin $ReleaseVersion
        echo ""
    else
       echo "tag $ReleaseVersion already exist, please remove it and try again"
       echo "    git tag -d $ReleaseVersion"
       echo "    git push origin :refs/tags/$ReleaseVersion"
       exit 1
  fi
fi

PROFILE="rsops"
if [[ -n $2 ]]; then
  PROFILE=$2
fi

CN_PROFILE="rsopsbj"
if [[ -n $3 ]]; then
  CN_PROFILE=$3
fi

if [[ -n $PROFILE ]]; then
   AWS_CMD="aws --profile $PROFILE"
fi

if [[ -n $CN_PROFILE ]]; then
   AWS_CMD_CN="aws --profile $CN_PROFILE"
fi
REGION_G=ap-northeast-1
REGION_CN=cn-north-1
echo "AWS_CMD: $AWS_CMD, REGION_G: $REGION_G"
echo "AWS_CMD_CN: $AWS_CMD_CN, REGION_CN: $REGION_CN"

AWS_ACCOUNT_ID=$(${AWS_CMD} sts get-caller-identity --region ${REGION_G}  --query Account --output text)
AWS_ACCOUNT_ID_CN=$(${AWS_CMD_CN} sts get-caller-identity --region ${REGION_CN} --query Account --output text)

echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
echo "AWS_ACCOUNT_ID_CN: $AWS_ACCOUNT_ID_CN"

#echo "Please confirm your AWS profile, region and account id, continue[n|y]:"
#read REPLEY
#
#if [[ $REPLEY =~ ^y ]]; then
#  echo ""
#else
#  echo "abort"
#  exit 0
#fi

version_id=$(git rev-parse HEAD)
echo $version_id > $version_id

todayStr=$(date +"%Y-%m-%d")
bucket_G=aws-gcr-rs-sol-workshop-ap-northeast-1-common
bucket_CN=aws-gcr-rs-sol-workshop-cn-north-1-common

echo "$version_id"
echo "$todayStr"

code_url='https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/main.zip'
cn_code_url='https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/rs-dev-workshop-code/latest/main.zip'

today_code_url="https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/${todayStr}/main.zip"
cn_today_code_url="https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/rs-dev-workshop-code/${todayStr}/main.zip"

github_code_url="https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip"

if [[ $ReleaseVersion =~ v.* ]];then
   release_code_url="https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/release/${ReleaseVersion}/main.zip"
   cn_release_code_url="https://aws-gcr-rs-sol-workshop-cn-north-1-common.s3.cn-north-1.amazonaws.com.cn/rs-dev-workshop-code/release/${ReleaseVersion}/main.zip"
fi

echo "cdk synth RsRawEC2CdkStack ..."
cdk synth RsRawEC2CdkStack > rs-raw-ec2.yaml
sed -i -e 's/SsmParameterValueawsserviceamiamazonlinuxlatestamzn2ami.*Parameter/SsmParameterValueForImageId/g' ./rs-raw-ec2.yaml

EC2_PHYSICALNAME_ID=$(cat ./rs-raw-ec2.yaml | egrep -o "gcrRsDevWorkshopEc2Ec2Instance[0-9a-fA-F]+" | head -1)
echo "EC2_PHYSICALNAME_ID: $EC2_PHYSICALNAME_ID"

if [[ -z $EC2_PHYSICALNAME_ID ]]; then
  echo "Error!!! cannot find EC2_PHYSICALNAME_ID"
  exit 1
fi

sed -i -e "s/__EC2_PHYSICALNAME_ID__/$EC2_PHYSICALNAME_ID/g" ./rs-raw-ec2.yaml
sed -i -e "s/Fn::Base64:/Fn::Base64: !Sub/g"  ./rs-raw-ec2.yaml

# latest
$AWS_CMD s3 cp ./rs-raw-ec2.yaml s3://${bucket_G}/rs-dev-workshop-code/latest/ --acl public-read
$AWS_CMD_CN s3 cp ./rs-raw-ec2.yaml s3://${bucket_CN}/rs-dev-workshop-code/latest/ --acl public-read
sed -e "s#$code_url#$cn_code_url#g" ./rs-raw-ec2.yaml > ./cn-latest-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./cn-latest-rs-raw-ec2.yaml s3://${bucket_G}/rs-dev-workshop-code/latest/cn-rs-raw-ec2.yaml --acl public-read
$AWS_CMD_CN s3 cp ./cn-latest-rs-raw-ec2.yaml s3://${bucket_CN}/rs-dev-workshop-code/latest/cn-rs-raw-ec2.yaml --acl public-read


# todayStr: yyyy-mm-dd
sed -e "s#$code_url#$today_code_url#g" ./rs-raw-ec2.yaml > ./${todayStr}-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./${todayStr}-rs-raw-ec2.yaml s3://${bucket_G}/rs-dev-workshop-code/${todayStr}/rs-raw-ec2.yaml --acl public-read
$AWS_CMD_CN s3 cp ./${todayStr}-rs-raw-ec2.yaml s3://${bucket_CN}/rs-dev-workshop-code/${todayStr}/rs-raw-ec2.yaml --acl public-read
sed -e "s#$code_url#$cn_today_code_url#g" ./rs-raw-ec2.yaml > ./cn-${todayStr}-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./cn-${todayStr}-rs-raw-ec2.yaml s3://${bucket_G}/rs-dev-workshop-code/${todayStr}/cn-rs-raw-ec2.yaml --acl public-read
$AWS_CMD_CN s3 cp ./cn-${todayStr}-rs-raw-ec2.yaml s3://${bucket_CN}/rs-dev-workshop-code/${todayStr}/cn-rs-raw-ec2.yaml --acl public-read

# github main
sed -e "s#$code_url#$github_code_url#g" ./rs-raw-ec2.yaml > ./github-rs-raw-ec2.yaml
$AWS_CMD s3 cp ./github-rs-raw-ec2.yaml s3://${bucket_G}/rs-dev-workshop-code/github/main/rs-raw-ec2.yaml --acl public-read
$AWS_CMD_CN s3 cp ./github-rs-raw-ec2.yaml s3://${bucket_CN}/rs-dev-workshop-code/github/main/rs-raw-ec2.yaml --acl public-read


rm main.zip > /dev/null 2>&1 || true

# code

wget https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip || {
   echo "fail to download recommender-system-dev-workshop-code"
   exit 1
 }


$AWS_CMD s3 cp main.zip  s3://${bucket_G}/rs-dev-workshop-code/latest/ --acl public-read
$AWS_CMD s3 cp main.zip  s3://${bucket_G}/rs-dev-workshop-code/${todayStr}/ --acl public-read
$AWS_CMD_CN s3 cp main.zip  s3://${bucket_CN}/rs-dev-workshop-code/latest/ --acl public-read
$AWS_CMD_CN s3 cp main.zip  s3://${bucket_CN}/rs-dev-workshop-code/${todayStr}/ --acl public-read


if [[ $ReleaseVersion =~ v.* ]]; then
    echo "release $ReleaseVersion"
    sed -e "s#$code_url#$release_code_url#g" ./rs-raw-ec2.yaml > ./release-rs-raw-ec2.yaml
    $AWS_CMD s3 cp ./release-rs-raw-ec2.yaml  s3://${bucket_G}/rs-dev-workshop-code/release/$ReleaseVersion/rs-raw-ec2.yaml --acl public-read
    $AWS_CMD_CN s3 cp ./release-rs-raw-ec2.yaml  s3://${bucket_CN}/rs-dev-workshop-code/release/$ReleaseVersion/rs-raw-ec2.yaml --acl public-read
    sed -e "s#$code_url#$cn_release_code_url#g" ./rs-raw-ec2.yaml > ./cn-release-rs-raw-ec2.yaml
    $AWS_CMD s3 cp ./cn-release-rs-raw-ec2.yaml  s3://${bucket_G}/rs-dev-workshop-code/release/$ReleaseVersion/cn-rs-raw-ec2.yaml --acl public-read
    $AWS_CMD_CN s3 cp ./cn-release-rs-raw-ec2.yaml  s3://${bucket_CN}/rs-dev-workshop-code/release/$ReleaseVersion/cn-rs-raw-ec2.yaml --acl public-read

    $AWS_CMD s3 cp main.zip s3://${bucket_G}/rs-dev-workshop-code/release/$ReleaseVersion/ --acl public-read
    $AWS_CMD_CN s3 cp main.zip s3://${bucket_CN}/rs-dev-workshop-code/release/$ReleaseVersion/ --acl public-read

    $AWS_CMD s3 cp $version_id s3://${bucket_G}/rs-dev-workshop-code/release/$ReleaseVersion/
    $AWS_CMD_CN s3 cp $version_id s3://${bucket_CN}/rs-dev-workshop-code/release/$ReleaseVersion/

    rm -rf ./doc/ > /dev/null 2>&1  || true
    mkdir ./doc/
    cd ./doc/
    wget https://github.com/gcr-solutions/recommender-system-dev-workshop/archive/refs/heads/main.zip || {
       echo "fail to download recommender-system-dev-workshop"
       exit 1
    }
    $AWS_CMD s3 cp ./main.zip s3://${bucket_G}/rs-dev-workshop-code/release/$ReleaseVersion/doc/
    $AWS_CMD_CN s3 cp ./main.zip s3://${bucket_CN}/rs-dev-workshop-code/release/$ReleaseVersion/doc/
    cd ..
    rm -rf ./doc/
fi

rm main.zip
rm rs-raw-ec2.yaml.*e > /dev/null 2>&1  || true
rm $version_id

if [[ -z $_DEBUG ]];then
    rm ./cn-latest-rs-raw-ec2.yaml  ${todayStr}-rs-raw-ec2.yaml  cn-${todayStr}-rs-raw-ec2.yaml github-rs-raw-ec2.yaml
    rm ./release-rs-raw-ec2.yaml ./cn-release-rs-raw-ec2.yaml > /dev/null 2>&1  || true
fi

echo ""
echo "Global region:"

echo "https://${bucket_G}.s3.${REGION_G}.amazonaws.com/rs-dev-workshop-code/latest/rs-raw-ec2.yaml"
echo "https://${bucket_G}.s3.${REGION_G}.amazonaws.com/rs-dev-workshop-code/${todayStr}/rs-raw-ec2.yaml"
echo "https://${bucket_G}.s3.${REGION_G}.amazonaws.com/rs-dev-workshop-code/github/main/rs-raw-ec2.yaml"

if [[ $ReleaseVersion =~ v.* ]]; then
      echo "https://${bucket_G}.s3.${REGION_G}.amazonaws.com/rs-dev-workshop-code/release/$ReleaseVersion/rs-raw-ec2.yaml"
fi

echo ""
echo "China region"

echo "https://${bucket_CN}.s3.${REGION_CN}.amazonaws.com.cn/rs-dev-workshop-code/latest/cn-rs-raw-ec2.yaml"
echo "https://${bucket_CN}.s3.${REGION_CN}.amazonaws.com.cn/rs-dev-workshop-code/${todayStr}/cn-rs-raw-ec2.yaml"
echo "https://${bucket_CN}.s3.${REGION_CN}.amazonaws.com.cn/rs-dev-workshop-code/github/main/rs-raw-ec2.yaml"

if [[ $ReleaseVersion =~ v.* ]]; then
      echo "https://${bucket_CN}.s3.${REGION_CN}.amazonaws.com.cn/rs-dev-workshop-code/release/$ReleaseVersion/cn-rs-raw-ec2.yaml"
fi
