#!/usr/bin/env bash
set -e

cd codebuild

export EKS_DEV_CLUSTER=gcr-rs-dev-operation-cluster
export AWS_PROFILE=default
export REGION=$(aws configure get region)
eksctl utils write-kubeconfig --region $REGION --cluster $EKS_DEV_CLUSTER

./create-iam-role.sh
sleep 20
# 4 create code build project for each service
./register-to-codebuild.sh

cd ../