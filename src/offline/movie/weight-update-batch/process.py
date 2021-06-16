# %%writefile preprocessing.py

import argparse
import logging

import boto3

s3client = boto3.client('s3')

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)


def write_to_s3(filename, bucket, key):
    print("upload s3://{}/{}".format(bucket, key))
    with open(filename, 'rb') as f:  # Read in binary mode
        # return s3client.upload_fileobj(f, bucket, key)
        return s3client.put_object(
            ACL='bucket-owner-full-control',
            Bucket=bucket,
            Key=key,
            Body=f
        )


def write_str_to_s3(content, bucket, key):
    print("write s3://{}/{}, content={}".format(bucket, key, content))
    s3client.put_object(Body=str(content).encode("utf8"), Bucket=bucket, Key=key, ACL='bucket-owner-full-control')


def download_from_s3(filename, bucket, key):
    with open(filename, 'wb') as f:
        return s3client.download_fileobj(bucket, key, f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="app inputs and outputs")
    parser.add_argument("--bucket", type=str, help="s3 bucket")
    parser.add_argument("--prefix", type=str, help="s3 input key prefix")
    args = parser.parse_args()
    print("args:", args)
    bucket = args.bucket
    prefix = args.prefix
    if prefix.endswith("/"):
        prefix = prefix[:-1]

    print(f"bucket:{bucket}, prefix:{prefix}")
    logging.info("I'm running - OK")
