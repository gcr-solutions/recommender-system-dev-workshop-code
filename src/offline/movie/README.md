# Event offline design
1. 每日落盘后的batch process
    1. action-preprocessing: 清理用户数据
        1. 输入：
            1. s3上的用户数据
        2. 输出：
            1. action.csv
    2. inverted-list: 生成倒排索引（包含热度分析）
        1. 输入：
            1. basic/expand files
            2. （!!!, 分析迈科点击文件，产生热度信息）
        2. 输出：
            1. movie_id_movie_property_dict.pickle
            2. movie_category_movie_ids_dict.pickle
            3. movie_director_movie_ids_dict.pickle
            4. movie_actor_movie_ids_dict.pickle
            5. movie_language_movie_ids_dict.pickle
            6. movie_level_movie_ids_dict.pickle
            7. movie_year_movie_ids_dict.pickle
    3. portrai-batch: 用户画像更新
        1. 输入：
            1. action.csv
            2. user_embeddings.h5
            3. raw_embed_user_mapping.pickle
            4. raw_embed_item_mapping.pickle
            5. portrait.pickle （!!!, 需要提前准备！这个逻辑是更新portrait）
            6. movie_id_movie_property_dict.pickle
        2. 输出
            1. portrait.pickle
    4. weight-update-batch: 策略权重更新逻辑 (!!!, 还未完成，暂时用固定的recall_config.pickle)
        1. 输入：
            1. action.csv
            2. recall_config.pickle
        2. 输出:
            1. recall_config.pickle
    5. recall-batch
        1. 输入：
            1. action.csv 
            2. ub_item_vector.index
            3. embed_raw_item_mapping.pickle
            4. portrait.pickle
            5. recall_config.pickle
            6. movie_id_movie_property_dict.pickle
            7. movie_category_movie_ids_dict.pickle
            8. movie_director_movie_ids_dict.pickle
            9. movie_actor_movie_ids_dict.pickle
            10. movie_language_movie_ids_dict.pickle
            11. movie_level_movie_ids_dict.pickle
            12. movie_year_movie_ids_dict.pickle
        2. 输出：
            1. recall_batch_result.pickle
    6. rank-batch
        1. 输入：
            1. recall_batch_result.pickle
            2. movie_id_movie_feature_dict.pickle
            3. portrait.pickle
            4. model.tar.gz
        2. 输出
            1. rank_batch_result.pickle
    7. filter-batch
        1. 输入：
            1. recall_batch_result.pickle
            2. rank_batch_result.pickle
        2. 输出
            1. filter_batch_result.pickle

2. 新物品上线的batch process：加入feature
    1. inverted-list: 生成倒排索引（包含热度分析）
        1. 输入：
            1. basic/expand files (!!!!, 增加一个字段标记为新物品)
        2. 输出：
            1. movie_id_movie_property_dict.pickle
            2. movie_category_movie_ids_dict.pickle
            3. movie_director_movie_ids_dict.pickle
            4. movie_actor_movie_ids_dict.pickle
            5. movie_language_movie_ids_dict.pickle
            6. movie_level_movie_ids_dict.pickle
            7. movie_year_movie_ids_dict.pickle
    2. add-item-user-batch: 加入新的用户/物品逻辑
        1. 输入：
            1. basic/expand files
            2. 包含所有的用户数据（!!!, 暂时用action.csv替代）
        2. 输出：
            1. raw_embed_user_mapping.pickle
            2. raw_embed_item_mapping.pickle
            3. embed_raw_user_mapping.pickle
            4. embed_raw_item_mapping.pickle
    3. model-update-ub: 更新youtubeDNN模型
        1. 输入：
            1. action.csv
            2. raw_embed_user_mapping.pickle
            3. raw_embed_item_mapping.pickle
        2. 输出：
            1. user_embeddings.h5
            2. ub_item_embeddings.npy
            3. ub_item_vector.index
    4. item-feature-update-batch: 物品feature更新
        1. 输入：
            1. basic/expand files
            2. ub_item_embeddings.npy
            2. raw_embed_user_mapping.pickle
            3. raw_embed_item_mapping.pickle
        2. 输出：
            1. movie_id_movie_feature_dict.pickle
    5. model-update-deepfm: 更新deepfm模型
        1. 输入：
            1. action.csv
            2. movie_id_movie_feature_dict.pickle
            3. raw_embed_user_mapping.pickle
            4. raw_embed_item_mapping.pickle
            5. user_embeddings.h5
        2. 输出：
            1. model.tar.gz

3. 行为数据更新的model update：
    1. action-preprocessing: 清理用户数据
        1. 输入：
            1. s3上的用户数据
        2. 输出：
            1. action.csv
    2. model-update-ub: 更新youtubeDNN模型
        1. 输入：
            1. action.csv
            2. raw_embed_user_mapping.pickle
            3. raw_embed_item_mapping.pickle
        2. 输出：
            1. user_embeddings.h5
            2. ub_item_embeddings.npy
            3. ub_item_vector.index
    3. model-update-deepfm: 更新deepfm模型
        1. 输入：
            1. action.csv
            2. movie_id_movie_feature_dict.pickle
            3. raw_embed_user_mapping.pickle
            4. raw_embed_item_mapping.pickle
            5. user_embeddings.h5
        2. 输出：
            1. model.tar.gz

## S3 目录结构


bucket: xxxx

    |-- xxxx
        |-- region-1
            |-- feature
                |-- action 
                    |-- embed_raw_item_mapping.pickle
                    |-- embed_raw_user_mapping.pickle
                    |-- raw_embed_item_mapping.pickle
                    |-- raw_embed_user_mapping.pickle
                    |-- ub_item_embeddings.npy
                    |-- ub_item_vector.index
                |-- content
                    |-- vector
                        |-- review.index
                        |-- image.index
                    |-- inverted-list
                        |-- movie_id_movie_property_dict.pickle
                        |-- movie_category_movie_ids_dict.pickle
                        |-- movie_director_movie_ids_dict.pickle
                        |-- movie_actor_movie_ids_dict.pickle
                        |-- movie_language_movie_ids_dict.pickle
                        |-- movie_level_movie_ids_dict.pickle
                        |-- movie_year_movie_ids_dict.pickle
                |-- recommend-list
                    |-- movie
                        |-- recall_batch_result.pickle
                        |-- rank_batch_result.pickle
                        |-- filter_batch_result.pickle
                    |-- tv
                    |-- portrait
                        |-- portrait.pickle
            |-- model
                |-- recall
                    |-- recall_config.pickle
                    |-- youtubednn
                        |-- ub_user_embedding.h5 
                    |-- review
                    |-- image-similariy
                |-- rank
                    |-- action
                        |-- deepfm
                            |-- latest
                                |-- model.tar.gz
                        |-- xgboost
                    |-- content
                |-- filter
                    |-- filter_config.pickle
            |-- system
                |-- user-data
                    |-- clean
                        |-- latest
                            |-- action.csv
                    |-- action
                        |-- yyyy-mm-dd
                            |-- exposure
                            |-- play
                    |-- portrait
                        |-- ProfileMap.csv
                |-- item-data
                    |-- photo
                        |-- xxx.jpg
                    |-- basic
                        |-- 1.csv
                    |-- expand
                        |-- 1.xlsx
        |-- region-2
        |-- region-3
        ...

## 如何Setup offline

### 1. 创建CodeBuild

```sh

export PROFILE=<your_aws_profile>

cd recommender-system/hack/codebuild
# 创建 iam role for codebuild
./create-iam-role.sh

# 如果使用 github， 需要运行下面脚本，创建访问github repo的 SSM
./create-secrets.sh

# 如果使用 AWS CodeCommit， 需要做以下工作：
#
# 1. 创建一个 CodeCommit repo
#
# 2. checkin code 到你自己的 CodeCommit
#
# 3. 将 codebuild-template-offline-codecommit.json 中的内容，copy 到 codebuild-template-offline.json 中，覆盖原来的内容
#    修改 "location": "https://git-codecommit.ap-northeast-1.amazonaws.com/v1/repos/mk-test" 指向你自己的 repo
#
# 4. 修改 src/offline/**/buildspec.yaml 删除 secrets-manager
#
 
# 创建 code build
./register-to-codebuild-offline.sh
```

### 2. 配置数据 Bucket 以及第一层目录

```cd recommender-system/src/offline```

编辑如下两个文件  
``` 
lambda/config.json
step-funcs/config.json
```
   
### 3. build offline 模块
```sh
cd recommender-system/src/offline
./build_offline_all.sh
```
打开 AWS Codebuild 的console, 确保都运行成功。
在 region `ap-southeast-1` Codebuild 的 console 链接如下：
https://ap-southeast-1.console.aws.amazon.com/codesuite/codebuild/start?region=ap-southeast-1

### 4. Prepare data 
- Action 数据存放位置
``` 
s3://gcr-rs-ops-ap-southeast-1-522244679887/recommender-system-film-mk/1/system/user-data/action/2020-12-17/exposure/exposurelog.2020-12-17-17.0.csv
s3://gcr-rs-ops-ap-southeast-1-522244679887/recommender-system-film-mk/1/system/user-data/action/2020-12-17/play/playlog.2020-12-17-17.0.csv

```
- Item 数据存放位置
```
s3://gcr-rs-ops-ap-southeast-1-522244679887/recommender-system-film-mk/1/system/item-data/basic/1.csv
s3://gcr-rs-ops-ap-southeast-1-522244679887/recommender-system-film-mk/1/system/item-data/expand/1.xlsx
```

__注意__： Bucket `gcr-rs-ops-ap-southeast-1-522244679887` 和第一层folder `recommender-system-film-mk` 可以在下面两个文件配置：
```
src/offline/lambda/config.json
src/offline/step-funcs/config.json
```


### 5. 查看和运行StepFunc

打开 AWS statemachines 的console, 在 region `ap-southeast-1` 链接如下：

https://ap-southeast-1.console.aws.amazon.com/states/home?region=ap-southeast-1#/statemachines

点击 StepFunc "RS-OverallStepFunc" -> "Start execution"
输入如下Input：
```json
{
  "regionId": "1",
  "change_type": "ACTION"
}
```