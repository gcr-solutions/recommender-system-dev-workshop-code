# # 1. Provision EKS cluster 
eksctl create cluster -f ./eks/x86-nodes-config.yaml --profile $PROFILE

# 2 Create EKS cluster namespace
kubectl apply -f ../manifests/ns.yaml