export REGION=<region>
export EKS_CLUSTER=rs-beta
export PROFILE=<profile_name>
export SECRET_NAME=github-rs
export GITHUB_USER=<github_user>
export ACCESS_TOKEN=<github_access_token>
export APP_CONF_REPO=<repo_name>
export GITHUB_REPO_LINK=<github_repo_link>

input=$1

if [ $input = "eks" ]
then
    ./eks-cluster-setup.sh
elif [ $input = "istio" ]
then
    ./istio-setup.sh
elif [ $input = "efs" ]
then
    ./efs-setup.sh 
elif [ $input = "redis" ]
then
    ./elastic-cache-setup.sh
elif [ $input = "ci" ]
then
    ./code-build-setup.sh
elif [ $input = "cd" ]
then
    ./argo-cd-setup.sh
else
    echo "end"
fi



