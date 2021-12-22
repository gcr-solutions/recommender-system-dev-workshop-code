ARG REGISTRY_URI
FROM ${REGISTRY_URI}/sagemaker-spark-processing:3.0-cpu-py37-v1.3

ENV PYTHONUNBUFFERED=TRUE

WORKDIR /opt/ml/processing/input/code/

ADD process.py ./

ENTRYPOINT ["smspark-submit", "/opt/ml/processing/input/code/process.py"]

