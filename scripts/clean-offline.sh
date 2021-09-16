#!/usr/bin/env bash
#set -e

curr_dir=$(pwd)

Stage=$1
if [[ -z $Stage ]]; then
  Stage='dev-workshop'
fi

if [[ -z $REGION ]]; then
  export REGION='ap-northeast-1'
fi

echo "RS_KEEP_OFFLINE_LAMBDA: $RS_KEEP_OFFLINE_LAMBDA"


AWS_CMD='aws'

if [[ -n $PROFILE ]]; then
  AWS_CMD="aws --profile $PROFILE"
fi

echo "Stage=$Stage"
echo "REGION=$REGION"
echo "AWS_CMD=$AWS_CMD"

AWS_ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --region ${REGION} --query Account --output text)
if [[ $? -ne 0 ]]; then
  echo "error!!! can not get your AWS_ACCOUNT_ID"
  exit 1
fi

echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"


if [[ -z $RS_SCENARIO  ]];then
    RS_SCENARIO=news
fi

echo "RS_SCENARIO: $RS_SCENARIO"


sleep 3

echo "==== DELETE all codebuild projects ===="
cd ${curr_dir}/codebuild
./register-to-codebuild-offline-codecommit.sh $Stage DELETE

news_repo_names=(
  rs/news-inverted-list
  rs/news-action-preprocessing
  rs/news-add-item-batch
  rs/news-add-user-batch
  rs/news-dashboard
  rs/news-filter-batch
  rs/news-item-feature-update-batch
  rs/news-item-preprocessing
  rs/news-model-update-action
  rs/news-model-update-embedding
  rs/news-portrait-batch
  rs/news-prepare-training-data
  rs/news-rank-batch
  rs/news-recall-batch
  rs/news-user-preprocessing
)

movie_repo_names=(
  "rs/movie-action-preprocessing"
  "rs/movie-add-item-batch"
  "rs/movie-add-user-batch"
  "rs/movie-dashboard"
  "rs/movie-filter-batch"
  "rs/movie-inverted-list"
  "rs/movie-item-feature-update-batch"
  "rs/movie-item-preprocessing"
  "rs/movie-model-update-deepfm"
  "rs/movie-model-update-ub"
  "rs/movie-portrait-batch"
  "rs/movie-rank-batch"
  "rs/movie-recall-batch"
  "rs/movie-user-preprocessing"
)


if [[ $RS_SCENARIO == 'news' ]];then
  repo_names=${news_repo_names[@]}
elif [[ $RS_SCENARIO == 'movie' ]];then
  repo_names=${movie_repo_names[@]}
fi


echo "Delete ECR repositories ..."
for repo_name in ${repo_names[@]}; do
  if [[ "$AWS_ACCOUNT_ID" != '522244679887' ]]; then
    echo "Delete repo: '$repo_name ...'"
    $AWS_CMD ecr delete-repository --repository-name $repo_name --region ${REGION} --force >/dev/null 2>&1 || true
  else
    # our test  account: 522244679887
    echo "skip deleting repo: '$repo_name ...'"
  fi
done


echo "==== Clean sample data in S3 ===="
cd ${curr_dir}/../sample-data/
./clean_up.sh $Stage

echo "==== DELETE all Step funcs and ECR repos ===="
cd ${curr_dir}/../src/offline/
./clean_up.sh $Stage


#echo "==== DELETE Codebuild Role ===="
#cd ${curr_dir}/codebuild/
#./create-codebuild-role.sh $Stage 'DELETE'

echo "All offline resources were deleted"


if [[  -z $NOT_PRINTING_CONTROL_C ]];then
   echo "Please stop printing the log by typing CONTROL+C "
fi