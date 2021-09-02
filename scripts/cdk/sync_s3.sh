cdk --profile rsops synth RsRawEC2CdkStack > rs-raw-ec2.yaml
aws --profile rsops s3 cp ./rs-raw-ec2.yaml s3://aws-gcr-rs-sol-workshop-ap-northeast-1-common/

sed -i -e 's/SsmParameterValueawsserviceamiamazonlinuxlatestamzn2ami.*Parameter/SsmParameterValueForImageId/g' ./rs-raw-ec2.yaml
echo 'https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-raw-ec2.yaml'
rm ./rs-raw-ec2.yaml-e || true

