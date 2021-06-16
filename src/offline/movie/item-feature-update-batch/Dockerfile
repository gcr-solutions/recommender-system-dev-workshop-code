FROM python:3.6-slim-buster

RUN pip3 install pandas==1.1.5 scikit-learn==0.24.2 numpy==1.18.5 boto3==1.16.57 s3fs xlrd==1.2.0 openpyxl==3.0.7 tqdm==4.61.0
ENV PYTHONUNBUFFERED=TRUE

WORKDIR /code/

ADD item-feature-update-batch.py ./

ENTRYPOINT ["python3", "/code/item-feature-update-batch.py"]

