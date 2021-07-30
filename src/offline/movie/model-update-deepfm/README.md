训练运行逻辑
1. python model-update-deepfm.py
2. mkdir serve
3. python deepfm.py --data_dir ./ --servable_model_dir serve --log_steps 10 --num_epochs 1 --field_size 38 --feature_size 117581 --deep_layers '2,2,2'
4. 压缩serve下面的文件 -> deepfm_model.tar.gz
5. 上传至recommender-system-film-mk/1/model/rank/action/deepfm/latest/deepfm_model.tar.gz