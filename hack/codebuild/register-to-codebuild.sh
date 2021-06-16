#!/bin/bash


roleArn=`cat role.arn`
projects[0]="loader"
projects[1]="event"
projects[2]="filter"
projects[3]="portrait"
projects[4]="rank"
projects[5]="retrieve"
projects[6]="recall"
projects[7]="demo"
projects[8]="ui"

for project in ${projects[@]}
do 
    echo "Deleting ${project} from CodeBuild ..."
    aws codebuild --profile $PROFILE --region $REGION delete-project --name rs-${project}-build || true
    echo "Done."
    sleep 5

    echo "Re-creating ${project} into CodeBuild ..."
    sed -e "s|__app_name__|$project|g;s|__github_repo_link__|$GITHUB_REPO_LINK|g" ./codebuild-template.json > ./${project}-codebuild.json
    aws codebuild --profile $PROFILE --region $REGION create-project \
        --cli-input-json file://${project}-codebuild.json \
        --service-role ${roleArn}
    echo "Done." 
    sleep 5
    rm -f ${project}-codebuild.json

    echo "Activing webhook on Github with all events ..."
    aws codebuild --profile $PROFILE --region $REGION create-webhook \
        --project-name rs-${project}-build \
        --filter-groups '[
            [{"type": "EVENT", "pattern": "PUSH", "excludeMatchedPattern": false},{"type":"FILE_PATH","pattern": "src/'${project}'", "excludeMatchedPattern": false}],
        ]'
    echo "Done." 
done



