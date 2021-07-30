FROM python:3.6-slim-buster

RUN pip3 install pandas==1.1.5 scikit-learn==0.24.2 numpy==1.18.5 boto3==1.16.57 s3fs tqdm==4.61.0 faiss-cpu==1.6.4
ENV PYTHONUNBUFFERED=TRUE

WORKDIR /code/

ADD filter-batch.py ./


ENTRYPOINT ["python3", "/code/filter-batch.py"]
