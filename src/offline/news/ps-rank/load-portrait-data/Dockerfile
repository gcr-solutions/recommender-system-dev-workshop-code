FROM python:3.6-slim-buster

RUN pip3 install boto3==1.16.57

ENV PYTHONUNBUFFERED=TRUE


WORKDIR /opt/ml/processing/input/code/

ADD load-portrait-data.py ./

ENTRYPOINT ["python", "/opt/ml/processing/input/code/load-portrait-data.py"]

