echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
fi

echo "Stage=$Stage"

#repoName=rs/news-model-update-embedding-cpu
repoName=rs/news-model-update-embedding-gpu

../norm_build.sh $repoName $Stage
