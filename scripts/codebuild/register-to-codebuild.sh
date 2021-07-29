#!/bin/bash

roleArn=$(cat role.arn)
projects[0]="loader"
projects[1]="event"
projects[2]="filter"
projects[3]="portrait"
projects[4]="rank"
projects[5]="retrieve"
projects[6]="recall"
projects[7]="demo"
projects[8]="ui"
projects[9]="personalize"

for project in ${projects[@]}; do
    echo "Deleting ${project} from CodeBuild ..."
    aws codebuild delete-project --name gcr-rs-dev-workshop-${project}-build || true
    echo "Done."
    sleep 5

    echo "Re-creating ${project} into CodeBuild ..."
    sed -e "s|__app_name__|$project|g;s|__GITHUB_USER_NAME__|$GITHUB_USER|g" ./codebuild-template.json >./${project}-codebuild.json
    aws codebuild create-project \
        --cli-input-json file://${project}-codebuild.json \
        --service-role ${roleArn}
    echo "Done."
    sleep 5
    rm -f ${project}-codebuild.json

    if [ "$project" = "filter" ] || [ "$project" = "recall" ]; then
        sleep 20
        echo "Start build ${project}!"
        aws codebuild start-build --project-name gcr-rs-dev-workshop-${project}-build
    fi
    sleep 10
    echo "Activing webhook on Github with all events ..."
    aws codebuild create-webhook \
        --project-name gcr-rs-dev-workshop-${project}-build \
        --filter-groups '[
            [{"type": "EVENT", "pattern": "PUSH", "excludeMatchedPattern": false},{"type":"FILE_PATH","pattern": "src/'${project}'", "excludeMatchedPattern": false}]
        ]'
    echo "Done."
done
