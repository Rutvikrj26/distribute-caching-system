import boto3
import logging
from moto import mock_s3, mock_cloudwatch
from config import Config
from werkzeug.datastructures import FileStorage
from datetime import datetime, timedelta
from operator import itemgetter

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# @mock_s3
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


# @mock_s3
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


# @mock_s3
def generate_presigned_url(key, bucket, expiry=1800):
    try:
        logging.info("Attempting to get presigned URL for uploaded image...")
        s3 = boto3.client('s3')
        image_url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=expiry)
    except Exception:
        logging.info(f"FAIL! Could not get url for image with key = {key}")
        image_url = None
    return image_url


# @mock_s3
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


# @mock_cloudwatch
def get_hits_and_misses_from_cloudwatch(period_in_minutes=1):
    try:
        logging.info("Sending hit/miss get request to Cloudwatch...")
        cloudwatch = boto3.client('cloudwatch', region_name=Config.AWS_REGION)
        graphing_data_hits = cloudwatch.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=period_in_minutes * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName=Config.hits,
            Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
            Statistics=['Sum'])
        HitsList = []
        for item in graphing_data_hits["Datapoints"]:
            Sum = item["Sum"]
            Time = item['Timestamp']
            Hits = [Time, Sum]
            HitsList.append(Hits)
        HitsList.sort(key=itemgetter(0))

        graphing_data_misses = cloudwatch.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=period_in_minutes * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName=Config.misses,
            Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
            Statistics=['Sum'])
        MissesList = []
        for item in graphing_data_misses["Datapoints"]:
            Sum = item["Sum"]
            Time = item['Timestamp']
            Misses = [Time, Sum]
            MissesList.append(Misses)
        MissesList.sort(key=itemgetter(0))
    except Exception:
        logging.info("CloudWatch Metric Query Error - Could not get memcache statistics to cloudwatch..." + str(inst))
        return None, None

    times = []
    hits = []
    misses = []

    for row in HitsList:
        times.append(row[0])
        hits.append(row[1])
    for miss in MissesList:
        misses.append(miss[1])

    logging.info("Successfully retrieved and parsed Cloudwatch metric data!")
    return hits, misses


# @mock_cloudwatch
def put_data_to_cloudwatch(metric_name, value, unit=None):
    if unit is None:
        unit = "None"
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
# @mock_cloudwatch
def log_memcache_stats(num_items, **stats):
    try:
            cloudwatch = boto3.client('cloudwatch', region_name=Config.AWS_REGION)
            cloudwatch.put_metric_data(
                MetricData=[
                    {
                        'MetricName': Config.hits,
                        'Unit': 'None',
                        'Timestamp': stats['timestamp'],
                        'Value': stats['hits']
                    },
                    {
                        'MetricName': Config.misses,
                        'Unit': 'None',
                        'Timestamp': stats['timestamp'],
                        'Value': stats['misses']
                    },
                    {
                        'MetricName': Config.num_posts_served,
                        'Unit': 'None',
                        'Timestamp': stats['timestamp'],
                        'Value': stats['posts_served']
                    },
                    {
                        'MetricName': Config.num_items_in_cache,
                        'Unit': 'None',
                        'Timestamp': stats['timestamp'],
                        'Value': num_items
                    },
                    {
                        'MetricName': Config.size_items_in_Megabytes,
                        'Unit': 'Megabytes',
                        'Timestamp': stats['timestamp'],
                        'Value': stats['cache_size']
                    },
                ],
                Namespace=Config.cloudwatch_namespace
            )

    except Exception as inst:
        logging.info("CloudWatch Metric Update Error - Could not upload memcache statistics to cloudwatch..." + str(type(inst)))
    return True

def get_memcache_stats():
        try:
            cloudwatch = boto3.client('cloudwatch', region_name=Config.AWS_REGION)
            graphing_data_hits = cloudwatch.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName=Config.hits,
                Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
                Statistics=['Sum'])
            HitsList = []
            for item in graphing_data_hits["Datapoints"]:
                Sum = item["Sum"]
                Time = item['Timestamp']
                Hits = [Time, Sum]
                HitsList.append(Hits)
            HitsList.sort(key=itemgetter(0))

            graphing_data_misses = cloudwatch.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName=Config.misses,
                Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
                Statistics=['Sum'])
            MissesList = []
            for item in graphing_data_misses["Datapoints"]:
                Sum = item["Sum"]
                Time = item['Timestamp']
                Misses = [Time, Sum]
                MissesList.append(Misses)
            MissesList.sort(key=itemgetter(0))

            graphing_data_posts_served = cloudwatch.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName=Config.num_posts_served,
                Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
                Statistics=['Sum'])
            NumPostsList = []
            for item in graphing_data_posts_served["Datapoints"]:
                Sum = item["Sum"]
                Time = item['Timestamp']
                NumPosts = [Time, Sum]
                NumPostsList.append(NumPosts)
            NumPostsList.sort(key=itemgetter(0))

            graphing_data_num_items = cloudwatch.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName=Config.num_items_in_cache,
                Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
                Statistics=['Sum'])
            NumItemsList = []
            for item in graphing_data_num_items["Datapoints"]:
                Sum = item["Sum"]
                Time = item['Timestamp']
                NumItems = [Time, Sum]
                NumItemsList.append(NumItems)
            NumItemsList.sort(key=itemgetter(0))

            graphing_data_cache_size = cloudwatch.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName=Config.size_items_in_Megabytes,
                Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
                Statistics=['Sum'])
            CacheSizesList = []
            for item in graphing_data_cache_size["Datapoints"]:
                Sum = item["Sum"]
                Time = item['Timestamp']
                CacheSizes = [Time, Sum]
                CacheSizesList.append(CacheSizes)
            CacheSizesList.sort(key=itemgetter(0))

            times = []
            hits = []
            misses = []
            posts = []
            num_items = []
            cache_sizes =[]

            for row in HitsList:
                times.append(row[0])
                hits.append(row[1])
            for miss in MissesList:
                misses.append(miss[1])
            for post in NumPostsList:
                posts.append(post[1])
            for item in NumItemsList:
                num_items.append(item[1])
            for size in CacheSizesList:
                cache_sizes.append(size[1])

            stats = list(zip(times, hits, misses, posts, num_items, cache_sizes))
            # for stat in stats:
            #      print(stat)
            h, m = get_hits_and_misses_from_cloudwatch()
            print(h)
            print(m)
        except Exception as inst:
            logging.info("CloudWatch Metric Query Error - Could not get memcache statistics to cloudwatch..." + str(inst))
        return stats