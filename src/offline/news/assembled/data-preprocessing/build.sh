
echo "------------------------------------------------ "
Stage=$1
if [[ -z $Stage ]];then
  Stage='dev'
fi

echo "Stage=$Stage"

repoName=rs/news-assembled-data-preprocessing

../../spark_build.sh $repoName $Stage