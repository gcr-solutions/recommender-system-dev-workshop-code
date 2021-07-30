#!/usr/bin/env bash

echo " == begin python deepfm.py  =="
cd /code/

mkdir serve
python deepfm.py --data_dir ./ --servable_model_dir serve --log_steps 10 --num_epochs 1 --field_size 38 --feature_size 117581 --deep_layers '2,2,2'
tar -cvf deepfm_model.tar  serve/
gzip deepfm_model.tar
echo " == done python deepfm.py  =="




