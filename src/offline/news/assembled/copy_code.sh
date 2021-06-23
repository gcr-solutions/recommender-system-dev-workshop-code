

cp -r ../add-item-batch ./data-preprocessing
cp -r ../item-preprocessing ./data-preprocessing
cp -r ../action-preprocessing ./data-preprocessing

rm ./data-preprocessing/*/*.sh
rm ./data-preprocessing/*/*.yaml
rm ./data-preprocessing/*/Dockerfile
rm ./data-preprocessing/*/*.ipynb > /dev/null 2>&1
rm ./data-preprocessing/*/*.txt > /dev/null 2>&1

#cp -r ../inverted-list ./train-model
cp -r ../item-feature-update-batch ./train-model
cp -r ../model-update-embedding  ./train-model

rm ./train-model/*/*.sh
rm ./train-model/*/*.yaml
rm ./train-model/*/Dockerfile
rm ./train-model/*/*.ipynb > /dev/null 2>&1
rm ./train-model/*/*.txt  > /dev/null 2>&1

