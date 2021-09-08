#!/bin/bash

echo "REGION:$REGION"

if [[ -z $REGION ]]; then
  echo "error ENV: REGION not set"
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID:$AWS_ACCOUNT_ID"

roleArn=$(cat _role.arn) ||  roleArn=''
if [[ -z $roleArn ]]; then
  roleArn="arn:${AWS_P}:iam::${AWS_ACCOUNT_ID}:role/gcr-rs-${Stage}-codebuild-role-$REGION"
fi

projects[0]="loader"
projects[1]="event"
projects[2]="filter"
projects[3]="portrait"
projects[4]="rank"
projects[5]="retrieve"
projects[6]="recall"
projects[7]="demo"
projects[8]="ui"

for project in ${projects[@]}; do
    echo "Deleting ${project} from CodeBuild ..."
    aws codebuild delete-project --name gcr-rs-dev-workshop-${project}-build || true
    echo "Done."
    sleep 5

    echo "Re-creating ${project} into CodeBuild ..."
    echo $REGION
    if [ $REGION = "cn-north-1" ] || [ $REGION = "cn-northwest-1" ]
    then
        echo "Create template for China regions!"
        sed -e "s|__app_name__|$project|g;s|__REGION__|$REGION|g;s|__REPO_NAME__|$APP_CONF_REPO|g" ./codebuild-template-cn.json >./${project}-codebuild.json        
    else
        echo "Create template for Global regions!"
        sed -e "s|__app_name__|$project|g;s|__REGION__|$REGION|g;s|__REPO_NAME__|$APP_CONF_REPO|g" ./codebuild-template.json >./${project}-codebuild.json
    fi 
    
    aws codebuild create-project \
        --cli-input-json file://${project}-codebuild.json \
        --service-role ${roleArn} > /dev/null
    echo "Done."
    sleep 5
    rm -f ${project}-codebuild.json

    echo "Start build ${project}!"
    aws codebuild start-build --project-name gcr-rs-dev-workshop-${project}-build > /dev/null
    sleep 10

    # echo "Activing webhook on Github with all events ..."
    # aws codebuild create-webhook \
    #     --project-name gcr-rs-dev-workshop-${project}-build \
    #     --filter-groups '[
    #         [{"type": "EVENT", "pattern": "PUSH", "excludeMatchedPattern": false},{"type":"FILE_PATH","pattern": "src/'${project}'", "excludeMatchedPattern": false}]
    #     ]'
    echo "Done."
done
