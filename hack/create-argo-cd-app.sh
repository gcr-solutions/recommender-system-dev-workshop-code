# region=$1
# profile_name=$2
# application_name=$3
# eks_namespace=$4
# path=$5
# github_repo=$6

export REGION=ap-southeast-1
export PROFILE=recommender-system-ops

echo PROFILE: $PROFILE
echo REGION: $REGION

SCENARIO_NAME=$1
STAGE_NAME=$2
GITHUB_REPO=$3

echo SCENARIO_NAME: $SCENARIO_NAME
echo STAGE_NAME: $STAGE_NAME
echo GITHUB_REPO: $GITHUB_REPO

APPLICATION_NAME=rs-$SCENARIO_NAME-$STAGE_NAME-application
echo APPLICATION_NAME: $APPLICATION_NAME
EKS_NAMESPACE=rs-$SCENARIO_NAME-$STAGE_NAME-ns
echo EKS_NAMESPACE: $EKS_NAMESPACE
KUSTOMIZE_CONFIG_PATH=manifests/envs/$SCENARIO_NAME-$STAGE_NAME
echo KUSTOMIZE_CONFIG_PATHth: $KUSTOMIZE_CONFIG_PATH


# 1 login argo cd server
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
elb_names=($(aws elb describe-load-balancers --region $REGION --profile $PROFILE --output text | grep LOADBALANCERDESCRIPTIONS |  awk '{print $6 }'))

echo "find $#elb_names elbs"

argocdserver_elb=''
for elb in ${elb_names[@]};
do
  echo "check elb $elb ..."
  aws elb describe-tags --region $REGION --profile $PROFILE --load-balancer-name $elb --output text  | grep 'argocd-server'
  if [[ $? -eq '0' ]];then
     echo "find argocd-server $elb"
     argocdserver_elb=$elb
     break
  fi
done

endpoint=$(aws elb describe-load-balancers --load-balancer-name $argocdserver_elb --region $REGION --profile $PROFILE --output text | grep LOADBALANCERDESCRIPTIONS | awk '{print $2 }')

echo user name: admin
echo password: $ARGOCD_PASSWORD
echo endpoint: $endpoint

argocd --insecure login $endpoint:443 --username admin --password $ARGOCD_PASSWORD

# # 2 Create argocd application
argocd app create $APPLICATION_NAME --repo $GITHUB_REPO --path $KUSTOMIZE_CONFIG_PATH --dest-namespace \
$EKS_NAMESPACE --dest-server https://kubernetes.default.svc --kustomize-image gcr.io/heptio-images/ks-guestbook-demo:0.1

