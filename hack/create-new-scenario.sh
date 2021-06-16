export REGION=ap-southeast-1
export EKS_CLUSTER=rs-beta
export PROFILE=recommender-system-ops

SCENARIO_NAME=$1
STAGE_NAME=$2

echo SCENARIO_NAME: $SCENARIO_NAME
echo STAGE_NAME: $STAGE_NAME

#get account_id
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile $PROFILE --o text | awk '{print $1}')

echo AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID

# ## create S3 bucket
BUCKET_BUILD=aws-gcr-rs-sol-$STAGE_NAME-$REGION-$AWS_ACCOUNT_ID
echo BUCKET_BUILD: $BUCKET_BUILD

echo "Create S3 Bucket: ${BUCKET_BUILD} if not exist"
aws s3 mb s3://${BUCKET_BUILD} --profile $PROFILE  >/dev/null 2>&1

# ## create Elastic Cache Redis
echo "create ElasticCache for Redis"
CACHE_CLUSTER_ID=rs-redis-cluster-$SCENARIO_NAME-$STAGE_NAME
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --profile $PROFILE --filter Name=group-name,Values=rs-redis-sg --query 'SecurityGroups[*].[GroupId]' --output text)

# aws elasticache --profile $PROFILE create-cache-cluster \
#   --cache-cluster-id rs-redis-cluster-$SCENARIO_NAME-$STAGE_NAME \
#   --cache-node-type cache.r6g.xlarge \
#   --engine redis \
#   --engine-version 6.x \
#   --num-cache-nodes 1 \
#   --region $REGION \
#   --cache-parameter-group default.redis6.x \
#   --security-group-ids $SECURITY_GROUP_ID \
#   --cache-subnet-group-name rs-redis-subnet-group


REDIS_ENDPOINT=""
while [ "$REDIS_ENDPOINT" = "" ]
do
   echo "wait for elastic cache for redis creating"
   sleep 10
   REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --region $REGION --profile $PROFILE --cache-cluster-id rs-redis-cluster-$SCENARIO_NAME-$STAGE_NAME --show-cache-node-info \
--query "CacheClusters[].CacheNodes[].Endpoint.Address" --output text)
  sleep 2
done

echo REDIS_ENDPOINT: $REDIS_ENDPOINT

cd ../manifests

## create ingress gateway
echo "      
      - enabled: true
        name: istio-ingressgateway-$SCENARIO_NAME-$STAGE_NAME
        label:
          istio: ingressgateway-$SCENARIO_NAME-$STAGE_NAME
" >> ingress-gateway.yaml

kubectl apply -f ingress-gateway.yaml

elb_names=$(aws elb describe-load-balancers --region $REGION --profile $PROFILE --output text | grep LOADBALANCERDESCRIPTIONS |  awk '{print $6 }')

echo "find $#elb_names elbs"

ingressgateway_elb=''
for elb in ${elb_names[@]};
do
  echo "check elb $elb ..."
  aws elb describe-tags --load-balancer-name $elb --region $REGION --profile $PROFILE --output text  | grep "istio-ingressgateway-$SCENARIO_NAME-$STAGE_NAME"
  if [[ $? -eq '0' ]];then
    ingressgateway_elb=$elb
    break
  fi
done

INGRESS_GATEWAY_ENDPOINT=$(aws elb describe-load-balancers --load-balancer-name $ingressgateway_elb --region $REGION --profile $PROFILE --output text | grep LOADBALANCERDESCRIPTIONS | awk '{print $2 }')

echo "INGRESS_GATEWAY_ENDPOINT: $INGRESS_GATEWAY_ENDPOINT"

# #copy config
cd envs
if [ ! -d "$SCENARIO_NAME-$STAGE_NAME" ]; then
  mkdir $SCENARIO_NAME-$STAGE_NAME
fi
cp -rf default/* $SCENARIO_NAME-$STAGE_NAME/
#replace config
cd $SCENARIO_NAME-$STAGE_NAME/efs

sed 's/__EFS-PV__/'"efs-pv-$SCENARIO_NAME-$STAGE_NAME"'/g' csi-env.yaml > csi-env.yaml.bak && mv csi-env.yaml.bak csi-env.yaml
sed 's/__EFS-SC__/'"efs-sc-$SCENARIO_NAME-$STAGE_NAME"'/g' pv-claim.yaml > pv-claim.yaml.bak && mv pv-claim.yaml.bak pv-claim.yaml
sed 's/__EFS-PV__/'"efs-pv-$SCENARIO_NAME-$STAGE_NAME"'/g' pv.yaml > pv.yaml.bak && mv pv.yaml.bak pv.yaml
sed 's/__EFS-SC__/'"efs-sc-$SCENARIO_NAME-$STAGE_NAME"'/g' pv.yaml > pv.yaml.bak && mv pv.yaml.bak pv.yaml
sed 's/__EFS-SC__/'"efs-sc-$SCENARIO_NAME-$STAGE_NAME"'/g' storage-class.yaml > storage-class.yaml.bak && mv storage-class.yaml.bak storage-class.yaml

# # #create pv, sc
echo "create pv, sc!"
kustomize build . |kubectl apply -f - 

cd ../
sed 's/__CONFIG-MAP-NAME__/'"rs-$SCENARIO_NAME-$STAGE_NAME-config"'/g' config.yaml > config.yaml.bak && mv config.yaml.bak config.yaml
sed 's/__ELASTIC-CACHE-REDIS__/'"$REDIS_ENDPOINT"'/g' config.yaml > config.yaml.bak && mv config.yaml.bak config.yaml
sed 's/__REGION__/'"$REGION"'/g' config.yaml > config.yaml.bak && mv config.yaml.bak config.yaml
sed 's/__S3-BUCKET__/'"$BUCKET_BUILD"'/g' config.yaml > config.yaml.bak && mv config.yaml.bak config.yaml
sed 's/__S3-BASE-FOLDER__/'"sample-data-$SCENARIO_NAME"'/g' config.yaml > config.yaml.bak && mv config.yaml.bak config.yaml
sed 's/__LOCAL_DATA_FOLDER__/'"$SCENARIO_NAME-$STAGE_NAME"'/g' config.yaml > config.yaml.bak && mv config.yaml.bak config.yaml

sed 's/__SELECTOR__/'"$SCENARIO_NAME-$STAGE_NAME"'/g' gateway.yaml > gateway.yaml.bak && mv gateway.yaml.bak gateway.yaml

cat kustomization.yaml | sed 's/__ESK-NAMESPACE__/'"rs-$SCENARIO_NAME-$STAGE_NAME-ns"'/g' kustomization.yaml > kustomization.yaml.bak && mv kustomization.yaml.bak kustomization.yaml
cat kustomization.yaml | sed 's/__CONFIG-NAME__/'"rs-$SCENARIO_NAME-$STAGE_NAME-config"'/g' kustomization.yaml > kustomization.yaml.bak && mv kustomization.yaml.bak kustomization.yaml

cat ns.yaml | sed 's/__ESK-NAMESPACE__/'"rs-$SCENARIO_NAME-$STAGE_NAME-ns"'/g' ns.yaml > ns.yaml.bak && mv ns.yaml.bak ns.yaml

#create namespace
echo "create eks namespace"
kubectl apply -f ns.yaml

cd ../../../src
# src code
SERVICE_WITH_PLUGIN="filter portrait rank recall"
for SERVICE in $SERVICE_WITH_PLUGIN
do
    cd $SERVICE/plugins
    if [ ! -d "$SCENARIO_NAME" ]; then
      mkdir $SCENARIO_NAME
    fi    
    cp news/* $SCENARIO_NAME/
    cd ../../
done

SERVICE_LIST="demo ui loader event retrieve filter portrait rank recall"
for SERVICE in $SERVICE_LIST
do
    cd $SERVICE
    sed "s/SCENARIOS:.*/SCENARIOS: \"news movie $SCENARIO_NAME\"/g" buildspec.yaml > buildspec.yaml.bak && mv buildspec.yaml.bak buildspec.yaml
    cd ../
done