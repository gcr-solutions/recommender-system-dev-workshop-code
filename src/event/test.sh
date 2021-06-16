curl -X POST -v -H "Content-Type: application/json" http://localhost:5100/api/v1/event/portrait/u008

curl -X POST -H "Content-Type: application/json" http://localhost:5100/api/v1/event/portrait/u008 -d '{
  "clicked_item": {
     "id": "item-00007",
     "subtype": "1"
  }
}'

curl -X POST -H "Content-Type: application/json" http://localhost:5100/api/v1/event/portrait/u008 -d '{
  "clicked_item": {
     "id": "item-00007",
     "subtype": "1"
  }
}'

curl -X POST -H "Content-Type: application/json" http://localhost:5100/api/v1/event/recall/u008 -d '{
  "clicked_item_list": [
     {
     "id": "item-00007",
     "subtype": "1"
     },
     {
     "id": "item-00008",
     "subtype": "1"
     }
  ]
}'

curl -X POST -H "Content-Type: application/json" http://localhost:5100/api/v1/event/start_train -d '{
  "change_type": "ACTION"
}'

curl -X POST -H "Content-Type: application/json" http://localhost:5100/api/v1/event/start_update -d '{
  "change_type": "RECOMMEND_LIST"
}'

curl -X POST -H "Content-Type: application/json" http://localhost:5100/api/v1/event/start_update -d '{
  "change_type": "RECOMMEND_LIST2"
}'

##############
##############

kubectl rollout restart deployment event -n rs-beta

kubectl get pods -n rs-beta | grep event

kubectl logs -n rs-beta -f $(kubectl get pods -n rs-beta | egrep -o 'event-[A-Za-z0-9-]+')

host="http://a6500b130ef7c45eb96f1727f55bafb6-1149103410.ap-southeast-1.elb.amazonaws.com"

curl -X GET -H "Content-Type: application/json" "$host/api/v1/event/portrait/13396"

curl -X POST -H "Content-Type: application/json" "$host/api/v1/event/portrait/13396" -d '{
  "clicked_item": {
     "id": "1690115"
  }
}'

curl -X POST -H "Content-Type: application/json" "$host/api/v1/event/recall/13396" -d '{
  "clicked_item_list": [
     {
     "id": "1690115"
     },
     {
     "id": "1692752"
     }
  ]
}'

#
# start_train
#

curl -X POST -H "Content-Type: application/json" -H "regionId: 1" \
  $host/api/v1/event/start_train -d '{
  "change_type": "ACTION"
}'

curl -X POST -H "Content-Type: application/json" -H "regionId: 1" \
  $host/api/v1/event/start_train -d '{
  "change_type": "CONTENT"
}'

curl -X POST -H "Content-Type: application/json" -H "regionId: 1" \
  $host/api/v1/event/start_train -d '{
  "change_type": "MODEL"
}'

#
# start_update
#

curl -X POST -H "Content-Type: application/json" -H "regionId: 1" \
  $host/api/v1/event/start_update -d '{
  "change_type": "ACTION"
}'

curl -X POST -H "Content-Type: application/json" -H "regionId: 1" \
  $host/api/v1/event/start_update -d '{
  "change_type": "CONTENT"
}'

curl -X POST -H "Content-Type: application/json" -H "regionId: 1" \
  $host/api/v1/event/start_update -d '{
  "change_type": "MODEL"
}'

