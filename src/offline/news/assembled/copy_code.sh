

cp -r ../user-preprocessing ./data-preprocessing
cp -r ../add-item-user-batch ./data-preprocessing
cp -r ../item-preprocessing ./data-preprocessing
cp -r ../action-preprocessing ./data-preprocessing

rm ./data-preprocessing/*/*.sh
rm ./data-preprocessing/*/*.yaml
rm ./data-preprocessing/*/Dockerfile
rm ./data-preprocessing/*/*.ipynb
rm ./data-preprocessing/*/*.txt



cp -r ../add-item-user-batch ./train-model
cp -r ../item-feature-update-batch  ./train-model
cp -r ../inverted-list ./train-model
cp -r ../model-update-embedding  ./train-model
cp -r ../model-update-action ./train-model

rm ./train-model/*/*.sh
rm ./train-model/*/*.yaml
rm ./train-model/*/Dockerfile
rm ./train-model/*/*.ipynb
rm ./train-model/*/*.txt