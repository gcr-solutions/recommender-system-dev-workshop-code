#!/usr/bin/env bash
set -e

echo "------------------------------------------------ "
echo $0
pwd

repoName=$1

if [[ -z ${repoName} ]];then
  echo "error repoName is empty"
  echo "Usage: $0 <repoName> <Stage>"
  exit 1
fi

echo "repoName: $repoName"

Stage=$2
if [[ -z $Stage ]];then
  echo "error $Stage is empty"
  echo "Usage: $0 <repoName> <Stage>"
  exit 1
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
  REGION='ap-southeast-1'
fi

echo "AWS_CMD:'$AWS_CMD'"
echo "REGION: '$REGION'"

AWS_REGION=$REGION
tag=$Stage

account_id=$($AWS_CMD sts get-caller-identity --query Account --output text)

if [[ $AWS_REGION =~ ^cn.* ]]; then
  account_ecr_uri=${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com.cn
else
  account_ecr_uri=${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com
fi


IMAGEURI=${account_ecr_uri}/$repoName:${tag}
LATEST_IMAGEURI=${account_ecr_uri}/$repoName:latest

echo "IMAGEURI: $IMAGEURI"


create_repo () {
  name=$1
  region=$2
  public_access=$3

  echo "create_repo() - name: $name, region: $region, public_access: $public_access"

  $AWS_CMD ecr create-repository  \
  --repository-name $name \
  --image-scanning-configuration scanOnPush=true \
  --region $region >/dev/null 2>&1 || true

  if [[ $public_access -eq '1' ]]; then
       $AWS_CMD ecr set-repository-policy  --repository-name $name --region $region --policy-text \
       '{
         "Version": "2008-10-17",
         "Statement": [
             {
                 "Sid": "AllowPull",
                 "Effect": "Allow",
                 "Principal": "*",
                 "Action": [
                     "ecr:GetDownloadUrlForLayer",
                     "ecr:BatchGetImage"
                 ]
             }
         ]
       }'
  fi
}

#
# https://github.com/aws/sagemaker-spark-container/blob/master/available_images.md
#

create_repo $repoName $AWS_REGION

if [[ $AWS_REGION == 'us-east-1' ]]; then
  registry_uri=173754725891.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'us-east-2' ]]; then
  registry_uri=314815235551.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'ap-northeast-1' ]]; then
  registry_uri=411782140378.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'ap-northeast-2' ]]; then
  registry_uri=860869212795.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'ap-southeast-1' ]]; then
  registry_uri=759080221371.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'ap-southeast-2' ]]; then
  registry_uri=440695851116.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'ap-east-1' ]]; then
  registry_uri=732049463269.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'cn-north-1' ]]; then
  registry_uri=671472414489.dkr.ecr.cn-north-1.amazonaws.com.cn
elif [[ $AWS_REGION == 'cn-northwest-1' ]]; then
  registry_uri=844356804704.dkr.ecr.cn-northwest-1.amazonaws.com.cn
elif [[ $AWS_REGION == 'us-west-1' ]]; then
  registry_uri=667973535471.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'us-west-2' ]]; then
  registry_uri=153931337802.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'ap-south-1' ]]; then
  registry_uri=105495057255.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'af-south-1' ]]; then
  registry_uri=309385258863.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'me-south-1' ]]; then
  registry_uri=750251592176.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'sa-east-1' ]]; then
  registry_uri=737130764395.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'ca-central-1' ]]; then
  registry_uri=446299261295.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'eu-central-1' ]]; then
  registry_uri=906073651304.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'eu-north-1' ]]; then
  registry_uri=330188676905.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'eu-west-1' ]]; then
  registry_uri=571004829621.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'eu-west-2' ]]; then
  registry_uri=836651553127.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'eu-south-1' ]]; then
  registry_uri=753923664805.dkr.ecr.${AWS_REGION}.amazonaws.com
elif [[ $AWS_REGION == 'eu-west-3' ]]; then
  registry_uri=136845547031.dkr.ecr.${AWS_REGION}.amazonaws.com
fi

echo registry_uri=$registry_uri

$AWS_CMD ecr get-login-password  --region ${AWS_REGION} | docker login --username AWS --password-stdin ${registry_uri}

docker build -t $repoName . --build-arg REGISTRY_URI=${registry_uri}

docker tag $repoName ${IMAGEURI}

echo ${IMAGEURI}

$AWS_CMD ecr get-login-password  --region ${AWS_REGION} | docker login --username AWS --password-stdin ${account_ecr_uri}

echo ">> push ${IMAGEURI}"
docker push ${IMAGEURI}

if [[ $? != 0 ]];then
     echo "Error docker push ${IMAGEURI}"
     exit 1
fi

if [[ $tag == 'dev' ]];then
  docker tag $repoName ${LATEST_IMAGEURI}
  echo ">> push ${LATEST_IMAGEURI}"
  docker push ${LATEST_IMAGEURI}

  if [[ $? != 0 ]];then
     echo "Error docker push ${LATEST_IMAGEURI}"
     exit 1
  fi
fi

version_id=$(git rev-parse HEAD)
VERSION_IMAGE=${account_ecr_uri}/$repoName:$version_id
docker tag ${repoName} ${VERSION_IMAGE}
echo ">> push ${VERSION_IMAGE}"
docker push ${VERSION_IMAGE}
