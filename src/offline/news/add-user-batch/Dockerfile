FROM public.ecr.aws/t8u1z3c8/python:3.8-slim

RUN pip3 install pandas==1.1.5 scikit-learn==0.24.2 numpy==1.18.5 boto3==1.16.57 s3fs tqdm==4.61.0
ENV PYTHONUNBUFFERED=TRUE


WORKDIR /opt/ml/processing/input/code/

ADD add-user-batch.py ./

ENTRYPOINT ["python", "/opt/ml/processing/input/code/add-user-batch.py"]

