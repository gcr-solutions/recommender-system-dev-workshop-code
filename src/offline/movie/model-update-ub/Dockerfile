#FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-training:1.15.5-gpu-py36-cu100-ubuntu18.04
#FROM 763104351884.dkr.ecr.ap-southeast-1.amazonaws.com/tensorflow-training:1.15.5-gpu-py36-cu100-ubuntu18.04

ARG REGISTRY_URI
FROM ${REGISTRY_URI}/tensorflow-training:1.15.5-gpu-py37-cu100-ubuntu18.04

RUN pip3 install tqdm==4.61.0 deepctr==0.8.2  deepmatch==0.2.0 faiss-gpu==1.7.1 pandas==1.1.5
ENV PYTHONUNBUFFERED=TRUE

WORKDIR /code/

ADD model-update-ub.py ./
ADD preprocess.py ./


ENTRYPOINT ["python3", "/code/model-update-ub.py"]
