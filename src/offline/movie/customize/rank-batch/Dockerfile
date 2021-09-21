ARG REGISTRY_URI
FROM ${REGISTRY_URI}/tensorflow-training:1.15.5-gpu-py37-cu100-ubuntu18.04

RUN pip3 install tqdm==4.61.0 deepctr==0.8.4 pandas==1.1.5
ENV PYTHONUNBUFFERED=TRUE

WORKDIR /code/

ADD rank-batch.py ./


ENTRYPOINT ["python3", "/code/rank-batch.py"]
