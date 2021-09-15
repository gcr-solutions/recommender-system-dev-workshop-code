FROM public.ecr.aws/t8u1z3c8/python:3.8-slim

RUN pip3 install boto3==1.16.57

ENV PYTHONUNBUFFERED=TRUE


WORKDIR /opt/ml/processing/input/code/

ADD load-portrait-data.py ./

ENTRYPOINT ["python", "/opt/ml/processing/input/code/load-portrait-data.py"]

