#!/usr/bin/env bash
set -e

dns_name=$(kubectl get svc istio-ingressgateway-news-dev -n istio-system -o=jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "endpoint: $dns_name"