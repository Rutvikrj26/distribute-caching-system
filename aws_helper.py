import boto3
import logging
from moto import mock_s3, mock_cloudwatch
from config import Config
from werkzeug.datastructures import FileStorage
from datetime import datetime, timedelta


@mock_s3
def upload_fileobj(key, file_storage_object, bucket):
    try:
        logging.info("Attempting to upload image to S3...")
        s3 = boto3.client('s3')
        s3.upload_fileobj(file_storage_object, bucket, key)
    except Exception:
        logging.info("S3 Error: Could not upload file object...")
        return False
    logging.info("S3 upload successful!")
    return True


@mock_s3
def download_fileobj(key, bucket):
    try:
        logging.info("Attempting to download image from S3...")
        my_file_storage = FileStorage()
        s3 = boto3.client('s3')
        s3.download_fileobj(bucket, key, my_file_storage)
    except Exception:
        logging.info("S3 Error - Could not download file object...")
        return None
    logging.info("S3 download object successful!")
    return my_file_storage


@mock_s3
def generate_presigned_url(key, bucket, expiry=1800):
    try:
        logging.info("Attempting to get presigned URL for uploaded image...")
        s3 = boto3.client('s3')
        image_url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=expiry)
    except Exception:
        logging.info(f"FAIL! Could not get url for image with key = {key}")
        image_url = None
    return image_url


@mock_s3
def delete_all_from_s3():
    try:
        logging.info("Getting all keys from S3...")
        s3 = boto3.client('s3')
        response = s3.list_objects_v2(Bucket=Config.S3_BUCKET_NAME)
        images = response["Contents"]
    except Exception:
        logging.info("ERROR! Not able to get all keys from S3...")
        return False
    try:
        images_to_delete = []
        for image in images:
            images_to_delete.append({"Key": image["Key"]})
        s3.delete_objects(Bucket=Config.S3_BUCKET_NAME, Delete={"Objects": images_to_delete})
    except Exception:
        logging.info("ERROR! Not able to delete all objects from S3...")
        return False
    logging.info("Successfully deleted all objects from S3!")
    return True


@mock_cloudwatch
def get_hits_and_misses_from_cloudwatch(period_in_minutes=1):
    period_in_seconds = period_in_minutes * 60
    end_time = datetime.now()
    start_time = end_time - timedelta(seconds=period_in_seconds)
    cloudwatch = boto3.client('cloudwatch')

    try:
        logging.info("Sending hit/miss get request to Cloudwatch...")
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': Config.hits,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'SITE/TRAFFIC',
                            'MetricName': Config.hits
                        },
                        'Period': 60,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False,
                    'Period': period_in_seconds
                },
                {
                    'Id': Config.misses,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'SITE/TRAFFIC',
                            'MetricName': Config.misses
                        },
                        'Period': 60,
                        'Stat': 'Sum'
                    },
                    'ReturnData': False,
                    'Period': period_in_seconds
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            ScanBy="TimeStampDescending",   # Returns the newest value first, use TimeStampAscending for oldest value first
            MaxDataPoints=200               # We shouldn't need more than 200 hits and misses for this
        )

        logging.info("Parsing data from Cloudwatch response...")
        metric_0_name = response['MetricDataResults'][0]['Id']
        metric_0_value = response['MetricDataResults'][0]['Values']
        metric_1_value = response['MetricDataResults'][1]['Values']
    except Exception:
        logging.info("ERROR! Could not get or parse data from Cloudwatch response...")
        return None, None

    if metric_0_name == Config.hits:
        hits = metric_0_value
        misses = metric_1_value
    else:
        hits = metric_1_value
        misses = metric_0_value

    logging.info("Successfully retrieved and parsed Cloudwatch metric data!")
    return hits, misses


@mock_cloudwatch
def put_data_to_cloudwatch(metric_name, value, unit=None):
    try:
        logging.info(f"Putting {metric_name} data with value {value} to Cloudwatch...")
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.put_metric_data(
            NameSpace='SITE/TRAFFIC',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Unit': unit,
                    'Value': value
                }
            ]
        )
    except Exception:
        logging.info("ERROR! Could not put metric data to Cloudwatch...")
        return False

    logging.info("Successfully put metric data to Cloudwatch!")
    return True
