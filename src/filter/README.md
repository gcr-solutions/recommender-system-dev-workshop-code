# Filter

## How to build pb/*.proto for Python


```bash

# Install dependency packages
$ pip3 install --user grpcio
$ pip3 install --user grpcio-tools

# Compile proto files
python3 -m grpc_tools.protoc -I./pb  --python_out=. --grpc_python_out=. ./pb/service.proto
python3 -m grpc_tools.protoc -I./pb  --python_out=. --grpc_python_out=. --experimental_allow_proto3_optional ./pb/service.proto

# Will generated 2 files: service_pb2_grpc.py & service_pb2.py

```

## How to use in your server & plugin

```
# Server.py

```

```
# plugin ?

```