ARG REGISTRY_URI
FROM ${REGISTRY_URI}/sagemaker-spark-processing:3.0-cpu-py37-v1.2
#FROM 173754725891.dkr.ecr.us-east-1.amazonaws.com/sagemaker-spark-processing:3.0-cpu-py37-v1.2

ENV PYTHONUNBUFFERED=TRUE

#RUN apt-get update && apt-get install -y && pip3 install --upgrade pip

COPY requirements.txt .
RUN pip3 install --user -r requirements.txt

WORKDIR /opt/ml/processing/input/code/

ADD . .

ENTRYPOINT ["smspark-submit", "/opt/ml/processing/input/code/run.py"]

