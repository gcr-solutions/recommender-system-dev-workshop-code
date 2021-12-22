# Recommender System v2.0

## Description
This is refactored Recommender System with plugin design, which means each moving pecieces are highly customizable.

## Architecture
![architecture](/images/architecture.png)

## Project Structure

    ├── CHANGELOG.md
    
    ├── CODE_OF_CONDUCT.md
    
    ├── CONTRIBUTING.md
    
    ├── NOTICE
    
    ├── README.md
    
    ├── manifests: files for infra
        ├── demo
            ├── demo-deployment.yaml
            ├── demo-service.yaml
            ├── kustomization.yaml
            └── virtual-service.yaml
        ├── efs
            └── driver-efs-cn.yaml
        ├── efs-to-be-remove
            ├── csi-env.yaml
        ├── kustomization.yaml
            ├── pv-claim.yaml
            ├── pv.yaml
            └── storage-class.yaml
        ├── envs
            ├── movie-dev
            └── news-dev
        ├── event
            ├── event-deployment.yaml
            ├── event-service.yaml
            ├── kustomization.yaml
            └── virtual-service.yaml
        ├── filter
            ├── filter-deployment.yaml
            ├── filter-service.yaml
            ├── kustomization.yaml
            └── virtual-service.yaml
        ├── loader
            ├── kustomization.yaml
            ├── loader-deployment.yaml
            ├── loader-service.yaml
            └── virtual-service.yaml
        ├── movie-istio-ingress-gateway.yaml
        ├── news-istio-ingress-gateway.yaml
        ├── portrait
            ├── kustomization.yaml
            ├── portrait-deployment.yaml
            ├── portrait-service.yaml
            └── virtual-service.yaml
        ├── rank
            ├── kustomization.yaml
            ├── rank-deployment.yaml
            ├── rank-service.yaml
            └── virtual-service.yaml
        ├── recall
            ├── kustomization.yaml
            ├── recall-deployment.yaml
            ├── recall-service.yaml
            └── virtual-service.yaml
        ├── redis
            ├── kustomization.yaml
            └── redis.yaml
        ├── redisinsight
            └── deployment.yaml
        └── retrieve
            ├── kustomization.yaml
            ├── retrieve-deployment.yaml
            ├── retrieve-service.yaml
            └── virtual-service.yaml

    ├── sample-data: sample for data for action/item/user data
        ├── clean_up.sh
        ├── feature
            ├── action
            ├── content
            ├── ps-recommend-list
            └── recommend-list
        ├── model
            ├── meta_files
            └── rank
        ├── new_item_to_s3.sh
        ├── new_news.csv
        ├── notification
            ├── action-model
            ├── embeddings
            ├── inverted-list
            ├── ps-result
            └── ps-sims-dict
        ├── sync_data_to_s3.sh
        ├── sync_movie_data_to_s3.sh
        └── system
            ├── action-data
            ├── dashboard
            ├── ingest-data
            ├── item-data
            ├── ps-config
            ├── ps-ingest-data
            └── user-data

    ├── scripts: scripts for deployment
        ├── README.md
        ├── cdk
            ├── 6e2a2c36824dd0d7417ef877ef69a15659c34116
            ├── README.md
            ├── bin
            ├── cdk.json
            ├── cdk.out
            ├── jest.config.js
            ├── lib
            ├── node_modules
            ├── package-lock.json
            ├── package.json
            ├── reset_code.sh
            ├── rs-raw-ec2.yaml
            ├── rs-raw-ec2.yaml-e
            ├── rs-raw-ec2.yamle
            ├── sync_s3.sh
            ├── test
            └── tsconfig.json
        ├── change-method.sh
        ├── change-recall-config-offline.sh
        ├── clean-offline.sh
        ├── clean-online.sh
        ├── cleanup-argocd-istio.sh
        ├── codebuild
            ├── assume-role.json
            ├── codebuild-role.yaml
            ├── codebuild-template-cn.json
            ├── codebuild-template-offline-codecommit.json
            ├── codebuild-template.json
            ├── create-codebuild-role.sh
            ├── create-iam-role-old.sh
            ├── create-secrets.sh
            ├── iam-role-policy.json
            ├── import-source-credential.sh
            ├── register-to-codebuild-offline-codecommit.sh
            └── register-to-codebuild.sh
        ├── create-argocd-application.sh
        ├── create-offline.sh
        ├── create-online-infra.sh
        ├── deploy-method.sh
        ├── eks
            ├── nodes-config-cn-template.yaml
            ├── nodes-config-template.yaml
            ├── nodes-config.yaml
            ├── nodes-dev-config-template.yaml
            └── nodes-dev-config.yaml
        ├── get-ingressgateway-elb-endpoint.sh
        ├── load-movie-seed-data.sh
        ├── load-news-seed-data.sh
        ├── online-code-build-setup.sh
        ├── personalize
            ├── clean-personalize.sh
            ├── create-personalize-role.sh
            ├── create-personalize.sh
            ├── ps_config_template-cn.json
            ├── ps_config_template.json
            ├── role
            ├── schema
            ├── update-ps-config.sh
            └── update-user-properties.sh
        ├── role
            ├── gcr-rs-role.json
            └── gcr-rs-user-role.json
        ├── setup-argocd-server.sh
        ├── setup-rs-system.sh
        ├── setup-ssm.sh
        ├── sync-method.sh
        ├── update-lambda-env.sh
        └── update-online-config.sh

    ├── src: core code for online/offline function
        ├── demo
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── requirements.txt
            └── server.py
        ├── event
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── docker-compose.yaml
            ├── requirements.txt
            ├── run_local.sh
            └── server.py
        ├── filter
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── pb
            ├── plugins
            ├── requirements.txt
            └── server.py
        ├── loader
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── requirements.txt
            ├── server.py
            └── test_loader.sh
        ├── offline
            ├── build.sh
            ├── buildspec.yaml
            ├── clean_up.sh
            ├── lambda
            ├── movie
            └── news
        ├── portrait
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── pb
            ├── plugins
            ├── requirements.txt
            └── server.py
        ├── rank
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── pb
            ├── plugins
            ├── requirements.txt
            └── server.py
        ├── recall
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── pb
            ├── plugins
            ├── requirements.txt
            └── server.py
        ├── retrieve
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── cache.py
            ├── docker-compose.yaml
            ├── pb
            ├── plugins
            ├── requirements.txt
            ├── run_local.sh
            └── server.py
        ├── swagger
            ├── api.yaml
            └── readme.md
        └── ui
            ├── Dockerfile
            ├── README.md
            ├── buildspec-commit.yaml
            ├── buildspec.yaml
            ├── package-lock.json
            ├── package.json
            ├── public
            ├── src
            └── tsconfig.json

79 directories, 185 files


## Contribution

See [CONTRIBUTING](./CONTRIBUTING.md) for more information.

## License


This project is licensed under the Apache-2.0 License.
