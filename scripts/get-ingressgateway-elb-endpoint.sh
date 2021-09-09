#!/usr/bin/env bash
set -e

echo "get elb $SCENARIO at $STAGE"

SCENATIO_STAGE=$SCENARIO-$STAGE

dns_name=$(kubectl get svc istio-ingressgateway-$SCENARIO_STAGE -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "endpoint: $dns_name"