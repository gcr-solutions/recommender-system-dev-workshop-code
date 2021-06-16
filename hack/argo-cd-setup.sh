# Setup ArgoCD
# 1 create namespace for argo cd
kubectl create namespace argocd
# 2 create argo cd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
# 3 get admin password
# kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server -o name | cut -d'/' -f 2
# 4 forward port to argocd server to local
# kubectl port-forward svc/argocd-server -n argocd 8080:443