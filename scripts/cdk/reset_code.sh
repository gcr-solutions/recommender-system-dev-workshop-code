#!/bin/bash

cd /home/ec2-user/environment
rm -rf ./recommender-system-dev-workshop-code/* > /dev/null 2>&1
rm -rf ./recommender-system-dev-workshop-code-main > /dev/null  2>&1
rm main.zip > /dev/null  2>&1

todayStr=$(date +"%Y-%m-%d")

# wget  https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/$todayStr/main.zip
wget  https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip

unzip main.zip

mv ./recommender-system-dev-workshop-code-main/* ./recommender-system-dev-workshop-code
rm -rf recommender-system-dev-workshop-code-main
cd ./recommender-system-dev-workshop-code/
git add . && git commit -m 'amend code' && git push
