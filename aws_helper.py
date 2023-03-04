import boto3
import logging
from moto import mock_s3
from config import Config
from werkzeug.datastructures import FileStorage


@mock_s3
def upload_fileobj(key, file_storage_object):
    try:
        s3 = boto3.client('s3')
        s3.upload_fileobj(file_storage_object, Config.S3_BUCKET_NAME, key)
    except Exception:
        logging.info("S3 Error: Could not upload file object...")
        return False
    logging.info("S3 upload successful!")
    return True


@mock_s3
def download_fileobj(key):
    try:
        my_file_storage = FileStorage()
        s3 = boto3.client('s3')
        s3.download_fileobj(Config.S3_BUCKET_NAME, key, my_file_storage)
    except Exception:
        logging.info("S3 Error - Could not download file object...")
        return None
    logging.info("S3 download object successful!")
    return my_file_storage
