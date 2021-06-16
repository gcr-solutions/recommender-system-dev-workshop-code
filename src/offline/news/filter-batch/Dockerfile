FROM python:3.6-slim-buster

RUN pip3 install pandas==1.1.5 scikit-learn numpy boto3 s3fs tqdm

ENV PYTHONUNBUFFERED=TRUE

RUN apt-get update && apt-get install -y && pip3 install --upgrade pip

WORKDIR /opt/ml/processing/input/code/

ADD filter-batch.py ./

ENTRYPOINT ["python", "/opt/ml/processing/input/code/filter-batch.py"]

