#!/usr/bin/env bash

user_dataset_import_job_status="ACTIVE"
item_dataset_import_job_status="ACTIVE"
interaction_dataset_import_job_status="ACTIVE"

MAX_TIME=30
CURRENT_TIME=0
while(( ${CURRENT_TIME} < ${MAX_TIME} )) 
do
    #user_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
    #            --dataset-import-job-arn ${user_dataset_import_job_arn} | jq '.datasetImportJob.status')
    #item_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
    #            --dataset-import-job-arn ${item_dataset_import_job_arn} | jq '.datasetImportJob.status')
    #interaction_dataset_import_job_status=$(aws personalize describe-dataset-import-job \
    #            --dataset-import-job-arn ${interaction_dataset_import_job_arn} | jq '.datasetImportJob.status')

    echo "user_dataset_import_job_status: ${user_dataset_import_job_status}"
    echo "item_dataset_import_job_status: ${item_dataset_import_job_status}"
    echo "interaction_dataset_import_job_status: ${interaction_dataset_import_job_status}"
    
    if [[ $user_dataset_import_job_status = "CREATE FAILED" || $item_dataset_import_job_status = "CREATE FAILED" || $interaction_dataset_import_job_status = "CREATE FAILED" ]]
    then
        echo "!!!Dataset Import Job Failed!!!"
        echo "!!!Personalize Service Create Failed!!!"
        exit 8
    elif [[ $user_dataset_import_job_status == "ACTIVE" && $item_dataset_import_job_status == "ACTIVE" && $interaction_dataset_import_job_status == "ACTIVE" ]]
    then
        echo "import job create successfully!"
        break
    fi
    sleep 5
    echo "sleep 5s..."
    CURRENT_TIME=`expr ${CURRENT_TIME} + 5`

done

if [ $CURRENT_TIME -ge $MAX_TIME ]
then
    echo "Import Job Time exceed 6 hours, please delete import job!"
fi

echo "test finish!"


