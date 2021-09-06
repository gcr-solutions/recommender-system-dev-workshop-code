#!/usr/bin/env bash
set -e

field_list=$(cat ./schema/NewsUserSchema.json | jq '.fields[].name' -r | xargs )
changed_field_list=$(echo ${field_list} | tr 'A-Z' 'a-z')

user_properties=""
for field in ${changed_field_list}
do
  if [[ "${field}" = "user_id" ]];
  then
    continue
  fi
  arr=(${field//_/ })
  len=${#arr[@]}
  res=${arr[0]}
  i=1
  while ((i < ${len}))
  do
    tmp=$(echo ${arr[$i]} | awk '{print toupper(substr($0,1,1))substr($0,2)}')
    res="${res}${tmp}"
    ((i++))
  done
  if [[ "${user_properties}" = "" ]];
  then
    user_properties="${res}"
  else
    user_properties="${user_properties},${res}"
  fi
done

curr_dir=$(pwd)
SCENARIO=news
config_file_path=${curr_dir}/../../sample-data/system/ps-config/ps_config.json
old_user_properties=$(awk -F"\"" '/UserProperties/{print $4}' $config_file_path)
echo "change old_user_properties: ${old_user_properties} to new_user_properties: ${user_properties}"
sed -e "s@$old_user_properties@$user_properties@g" -i "" $config_file_path > /dev/null
