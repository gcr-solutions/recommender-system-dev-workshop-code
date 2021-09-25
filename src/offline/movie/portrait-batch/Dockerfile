#FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-training:1.15.5-gpu-py36-cu100-ubuntu18.04
##FROM 763104351884.dkr.ecr.ap-southeast-1.amazonaws.com/tensorflow-training:1.15.5-gpu-py36-cu100-ubuntu18.04

ARG REGISTRY_URI
FROM ${REGISTRY_URI}/tensorflow-training:1.15.5-gpu-py37-cu100-ubuntu18.04

RUN pip3 install tqdm==4.61.0 deepmatch==0.2.0 pandas==1.1.5
ENV PYTHONUNBUFFERED=TRUE

WORKDIR /code/

ADD portrait-batch.py ./


ENTRYPOINT ["python3", "/code/portrait-batch.py"]
