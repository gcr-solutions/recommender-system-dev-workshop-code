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

news_dev="adf45c54cf8734c0f9c14f4adfecae86-234454018.ap-southeast-1.elb.amazonaws.com"
movie_dev="a4fb68ded64b0495f90bbaa36c7773cd-1545468192.ap-southeast-1.elb.amazonaws.com"

news_demo="a08ee0a80c43b4cf8af229bf3c70c995-1967456171.ap-southeast-1.elb.amazonaws.com"
movie_demo="a30667949998643caa071da69f042c8f-448313425.ap-southeast-1.elb.amazonaws.com"



curl -X POST -H "Content-Type: application/json" "$host/api/v1/event/portrait/u008" -d '{
  "clicked_item": {
     "id": "6552309039697494532",
     "subtype": "1"
  }
}'

curl -X POST -H "Content-Type: application/json" "$host/api/v1/event/recall/u008" -d '{
  "clicked_item_list": [
     {
     "id": "6552309039697494532",
     "subtype": "1"
     },
     {
     "id": "6552309039697494532",
     "subtype": "1"
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

# dashboard

host=http://$news_dev
curl -X GET -H "Content-Type: application/json" $host/api/v1/demo/dashboard

host=http://$news_demo
curl -X GET -H "Content-Type: application/json" $host/api/v1/demo/dashboard


host=http://$movie_dev
curl -X GET -H "Content-Type: application/json" $host/api/v1/demo/dashboard


host=http://$movie_demo
curl -X GET -H "Content-Type: application/json" $host/api/v1/demo/dashboard

