
# curl  -X GET -v -H "Content-Type: application/json" http://localhost:5600/api/v1/retrieve/u0007

# curl  -X GET -v -H "Content-Type: application/json" 'http://localhost:5600/api/v1/retrieve/u0007?curPage=1'

# curl  -X GET -v -H "Content-Type: application/json" 'http://localhost:5600/api/v1/retrieve/u0007?curPage=1&pageSize=1'


##############
##############


url="http://a6500b130ef7c45eb96f1727f55bafb6-1149103410.ap-southeast-1.elb.amazonaws.com/api/v1/retrieve/52a23a5a-9dc3-11eb-a364-acde48001122"

curl -XGET -H "Content-Type: application/json" ${url}
curl -XGET -H "Content-Type: application/json" "${url}?recommendType=recommend"

kubectl get pods -n rs-beta  | grep retrieve

kubectl logs -f retrieve-54fc7c96c8-g5c82 -n rs-beta
