export REGION=ap-southeast-1
export EKS_CLUSTER=rs-beta
export PROFILE=recommender-system-ops

SCENARIO_NAME=$1
STAGE_NAME=$2

echo SCENARIO_NAME: $SCENARIO_NAME
echo STAGE_NAME: $STAGE_NAME


SERVICE_WITH_PLUGIN="filter portrait rank recall"
for SERVICE in $SERVICE_WITH_PLUGIN
do
    rm -rf ../src/$SERVICE/plugins/$SCENARIO_NAME
done

kubectl delete -f ../manifests/envs/$SCENARIO_NAME-$STAGE_NAME/ns.yaml
rm -rf ../manifests/envs/$SCENARIO_NAME-$STAGE_NAME

cd ../
git restore .

kubectl delete pv/efs-pv-$SCENARIO_NAME-$STAGE_NAME
kubectl delete sc/efs-sc-$SCENARIO_NAME-$STAGE_NAME