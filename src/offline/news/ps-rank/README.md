# 数据落盘说明

## 点击数据落盘：

### 文件名：
system/ingest-data/action/action_xxxx.csv

### 数据格式：
``` 
user_id_!_item_id_!_timestamp_!_action_type_!_action_value_!_action_source
```
例如：
``` 
52a23654-9dc3-11eb-a364-acde48001122_!_6552332581256299016_!_1618472565_!_1_!_0_!_1
52a23654-9dc3-11eb-a364-acde48001122_!_6552130363123040771_!_1618467016_!_1_!_0_!_116
52a23654-9dc3-11eb-a364-acde48001122_!_6475484594673025293_!_1618462187_!_1_!_1_!_109
```

- action_type 点击 -> 1 (对新闻，都填1)

- action_value  点击 -> 1, 未点击 -> 0

- action_source  从哪个页面点击的， 推荐页面填 1， 其他页面填相应的code



## 新注册用户数据落盘：
### 文件名：
system/ingest-data/user/user_xxxx.csv

### 数据格式：
```
user_id_!_sex_!_age_!_timestamp_!_user_name
 ```
例如：
```
52a411f4-9dc3-11eb-a364-acde48001122_!_M_!_28_!_1616473808_!_alertMandrill5
 ```

- sex, age 如果没有，就随便填一个
- user_name 需要填写， 如果是匿名用户，填 ‘anonymous’