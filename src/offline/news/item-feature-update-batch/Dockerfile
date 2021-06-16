ARG REGISTRY_URI
FROM ${REGISTRY_URI}/tensorflow-training:1.15.3-cpu-py37-ubuntu18.04

ENV PYTHONUNBUFFERED=TRUE

RUN apt-get update && apt-get install -y && pip3 install --upgrade pip

COPY requirements.txt .
RUN pip3 install --user -r requirements.txt
RUN pip3 install --no-cache-dir dgl==0.4.3.post2
#RUN pip3 install -e git+http://git@github.com/xiaotinghe/fastHan.git'#egg=fastHan'
RUN pip3 install -e git+http://git@github.com/xiaotinghe/dgl-ke.git'#egg=dglke&subdirectory=python'


WORKDIR /opt/ml/processing/input/code/

ADD src/*.py ./

ENTRYPOINT ["python", "/opt/ml/processing/input/code/item-feature-update-batch.py"]

