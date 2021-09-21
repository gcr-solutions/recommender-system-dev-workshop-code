#!/usr/bin/env bash
set -e

export SECRET_NAME=gcr-rs-dev-workshop-secret
export APP_CONF_REPO=recommender-system-dev-workshop-code
export METHOD=customize
export SCENARIO=news
echo "APP_CONF_REPO: $APP_CONF_REPO"

if [[ -z $RS_SCENARIO  ]];then
    RS_SCENARIO=news
fi

export RS_SCENARIO=$RS_SCENARIO
echo "RS_SCENARIO: $RS_SCENARIO"

input=$1

if [ $input = "deploy-offline"  ]
then
    echo "start create offline!"
    ./create-offline.sh
elif [ $input = "online-codebuild" ]
then
     echo "start create online codebuild project!"
    ./online-code-build-setup.sh
elif [ $input = "infra" ]
then
    echo "start create online infrastructure!"
    ./create-online-infra.sh
elif [ $input = "config" ]
then
    echo "start update online config!"
    ./update-online-config.sh
elif [ $input = "argo-server" ]
then
    echo "start setup argocd server!"
    ./setup-argocd-server.sh
elif [ $input = "application" ]
then
    echo "start create application!"
    ./create-argocd-application.sh
elif [ $input = "load-data" ]
then
    echo "start load data!"
    ./load-seed-data.sh
elif [ $input = "ALL" ]
then
    echo "export SECRET_NAME=gcr-rs-dev-workshop-secret"
    echo "export APP_CONF_REPO=recommender-system-dev-workshop-code"
    echo "---------------------------------------------"
    export NOT_PRINTING_CONTROL_C="yes"
    echo ""
    echo "=== 1/7. start create offline!"
    echo "./create-online-infra.sh"
    ./create-offline.sh
    sleep 10

    echo ""
    echo "=== 2/7. start create online codebuild project!"
    echo "./create-online-infra.sh"
    ./online-code-build-setup.sh
    sleep 10

    echo ""
    echo "=== 3/7. start create online infrastructure!"
    echo "./create-online-infra.sh"
    ./create-online-infra.sh
    kubectl get node
    sleep 10

    echo ""
    echo "=== 4/7. start update online config!"
    echo "./update-online-config.sh"
    ./update-online-config.sh

    git pull
    git add ../manifests/envs/news-dev/config.yaml
    git commit -m "update config"
    git push
    sleep 10

    echo ""
    echo "=== 5/7. start setup argocd server!"
    echo "./setup-argocd-server.sh"
    ./setup-argocd-server.sh
    sleep 120

    echo ""
    echo "=== 6/7. start create application!"
    echo "./create-argocd-application.sh"
    ./create-argocd-application.sh
    sleep 120

    echo ""
    echo "=== 7/7. load-seed-data!"
    echo "./load-seed-data.sh"
    ./load-seed-data.sh

    ./get-ingressgateway-elb-endpoint.sh

    echo "=== ALL Complete ==="
else
    echo "Please enter correct parameter"
fi  