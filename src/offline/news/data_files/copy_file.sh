
# =================================
src_bucket=aws-gcr-rs-sol-demo-ap-southeast-1-522244679887
target_bucket=aws-gcr-rs-sol-demo-ap-northeast-1-080766874269

cd /Users/yonmzn/work/mk/recommender-system/src/offline/news/data_files

aws s3 cp item_ingest.csv s3://$target_bucket/sample-data/system/ingest-data/item/
aws s3 cp action_ingest.csv s3://$target_bucket/sample-data/system/ingest-data/action/
aws s3 cp user_ingest.csv s3://$target_bucket/sample-data/system/ingest-data/user/


cd /Users/yonmzn/work/rs_demo/data/data_files
aws --profile rsops s3 sync s3://$src_bucket/sample-data/model/meta_files/  .
aws s3 sync . s3://$target_bucket/sample-data/model/meta_files/  --acl bucket-owner-full-control

cd /Users/yonmzn/work/rs_demo/data/config_files

aws --profile rsops s3 cp s3://$src_bucket/sample-data/feature/recommend-list/portrait/portrait.pickle .
aws --profile rsops s3 cp s3://$src_bucket/sample-data/feature/content/inverted-list/filter_config.pickle .
aws --profile rsops s3 cp s3://$src_bucket/sample-data/feature/content/inverted-list/recall_config.pickle .

aws s3 cp portrait.pickle  s3://$target_bucket/sample-data/feature/recommend-list/portrait/portrait.pickle  --acl bucket-owner-full-control
aws s3 cp filter_config.pickle  s3://$target_bucket/sample-data/feature/content/inverted-list/filter_config.pickle --acl bucket-owner-full-control
aws s3 cp recall_config.pickle  s3://$target_bucket/sample-data/feature/content/inverted-list/recall_config.pickle --acl bucket-owner-full-control
















