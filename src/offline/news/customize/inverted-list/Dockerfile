ARG REGISTRY_URI
FROM ${REGISTRY_URI}/pytorch-inference:1.7.1-cpu-py36-ubuntu18.04
# FROM ${REGISTRY_URI}/pytorch-inference:1.8.1-cpu-py36-ubuntu18.04
# FROM ${REGISTRY_URI}/tensorflow-training:1.15.5-gpu-py37-cu100-ubuntu18.04

ENV PYTHONUNBUFFERED=TRUE

RUN apt-get update && apt-get install -y && pip3 install --upgrade pip

COPY requirements.txt .
RUN pip3 install --default-timeout=1800 --user -r requirements.txt
RUN pip3 install --no-cache-dir dgl==0.4.3.post2
#RUN pip3 install -e git+http://git@github.com/xiaotinghe/fastHan.git'#egg=fastHan'
RUN pip3 install -e git+http://git@github.com/xiaotinghe/dgl-ke.git'#egg=dglke&subdirectory=python'

COPY fasthan_base/* /opt/ml/fasthan_base/

WORKDIR /opt/ml/processing/input/code/

ADD src/* ./

ENTRYPOINT ["python", "/opt/ml/processing/input/code/inverted-list.py"]

