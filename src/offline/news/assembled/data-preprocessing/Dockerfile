ARG REGISTRY_URI
FROM ${REGISTRY_URI}/sagemaker-spark-processing:3.0-cpu-py37-v1.2
#FROM 173754725891.dkr.ecr.us-east-1.amazonaws.com/sagemaker-spark-processing:3.0-cpu-py37-v1.2

ENV PYTHONUNBUFFERED=TRUE

#RUN apt-get update && apt-get install -y && pip3 install --upgrade pip

COPY requirements.txt .
RUN pip3 install --user -r requirements.txt
#RUN pip3 install --no-cache-dir dgl==0.4.3.post2
##RUN pip3 install -e git+http://git@github.com/xiaotinghe/fastHan.git'#egg=fastHan'
#RUN pip3 install -e git+http://git@github.com/xiaotinghe/dgl-ke.git'#egg=dglke&subdirectory=python'


WORKDIR /opt/ml/processing/input/code/

ADD . .

ENTRYPOINT ["smspark-submit", "/opt/ml/processing/input/code/run.py"]

