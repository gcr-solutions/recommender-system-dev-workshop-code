#!/usr/bin/env bash
set -e

if [[ -z $Stage ]];then
  Stage='dev-workshop'
fi

if [[ -z $METHOD ]];then
  METHOD='customize'
fi

echo "METHOD: ${METHOD}"
echo "Stage: ${Stage}"


ps_status=$(ps aux | grep -i "create-personalize.sh" | grep -v "grep" | wc -l)
if [ $ps_status -ge 1 ]
   then
        echo "------Personalize Service is still creating------"
        echo "------Wait for completion------"
        MAX_TIME=`expr 2 \* 60 \* 60`
        CURRENT_TIME=0
        while(( ${CURRENT_TIME} < ${MAX_TIME} ))
        do
                status=$(ps aux | grep -i "create-personalize.sh" | grep -v "grep" | wc -l)

                if [ $status -lt 1 ]
                then
                        echo "Personalize Service Create Completely"
                        break
                fi

                CURRENT_TIME=`expr ${CURRENT_TIME} + 60`
                echo "wait for 1 minute ..."
                sleep 60
        done
fi

echo "Synchronize Method to Online Part"
./setup-rs-system.sh change-method ${METHOD}

echo "Please stop printing the log by typing CONTROL+C "

