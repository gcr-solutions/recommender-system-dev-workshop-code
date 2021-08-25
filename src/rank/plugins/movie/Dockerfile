# first stage
FROM public.ecr.aws/t8u1z3c8/python:3.7 AS builder
COPY requirements.txt .

# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --user -r requirements.txt
COPY ./ .
RUN python -m grpc_tools.protoc -I./pb  --python_out=. --grpc_python_out=. --experimental_allow_proto3_optional ./pb/service.proto
RUN pip uninstall -y grpcio-tools

# second unnamed stage
FROM public.ecr.aws/t8u1z3c8/python:3.7-slim
# FROM 763104351884.dkr.ecr.ap-southeast-1.amazonaws.com/tensorflow-training:1.15.5-gpu-py37-cu110-ubuntu18.04
# FROM 763104351884.dkr.ecr.ap-southeast-1.amazonaws.com/tensorflow-training:1.15.5-gpu-py36-cu100-ubuntu18.04
WORKDIR /code

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local/bin /root/.local
COPY --from=builder /root/.local/lib /root/.local
COPY --from=builder /*_pb2*.py ./
COPY ./ .



# update PATH environment variable
ENV PATH=/root/.local:$PATH
ENV PYTHONPATH=/root/.local:/root/.local/python3.7/site-packages

CMD [ "python", "./service.py" ]