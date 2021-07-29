# first stage
FROM public.ecr.aws/s2e6t6k5/python:3.8 AS builder
COPY requirements.txt .

# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --user -r requirements.txt
COPY ./ .
RUN python -m grpc_tools.protoc -I./pb  --python_out=. --grpc_python_out=. --experimental_allow_proto3_optional ./pb/service.proto
RUN pip uninstall -y grpcio-tools

# second unnamed stage
FROM public.ecr.aws/s2e6t6k5/python:3.8-slim
WORKDIR /code

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local/bin /root/.local
COPY --from=builder /root/.local/lib /root/.local
COPY --from=builder /*_pb2*.py ./
COPY ./ .



# update PATH environment variable
ENV PATH=/root/.local:$PATH
ENV PYTHONPATH=/root/.local:/root/.local/python3.8/site-packages

CMD [ "python", "./server.py" ]