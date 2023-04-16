import boto3
import logging
from config import Config
from datetime import datetime, timedelta
from operator import itemgetter
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


def download_fileobj(key, bucket):
    try:
        logging.info("Attempting to download object from S3...")
        s3 = boto3.client('s3')
        my_file_storage = s3.get_object(Bucket=bucket, Key=key)['Body']
    except Exception as e:
        logging.error("S3 Error - Could not download object: {}".format(e))
        return None
    logging.info("S3 download object successful!")
    return my_file_storage


def delete_all_from_s3(bucket):
    try:
        logging.info("Getting all keys from S3...")
        s3 = boto3.client('s3')
        response = s3.list_objects_v2(Bucket=bucket)
        images = response["Contents"]
    except Exception:
        logging.info("ERROR! Not able to get all keys from S3...")
        return False
    try:
        images_to_delete = []
        for image in images:
            images_to_delete.append({"Key": image["Key"]})
        s3.delete_objects(Bucket=bucket, Delete={"Objects": images_to_delete})
    except Exception:
        logging.info("ERROR! Not able to delete all objects from S3...")
        return False
    logging.info("Successfully deleted all objects from S3!")
    return True


def put_data_to_cloudwatch(metric_name, value, timestamp, unit=None):
    if unit is None:
        unit = "None"
    try:
            cloudwatch = boto3.client('cloudwatch', region_name=Config.AWS_REGION)
            cloudwatch.put_metric_data(
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Unit': unit,
                        'Timestamp': timestamp,
                        'Value': value
                    },
                ],
                Namespace=Config.cloudwatch_namespace
            )

    except Exception as inst:
        logging.info("CloudWatch Metric Update Error - Could not upload singular metric data to cloudwatch..." + str((inst)))
        return False
    logging.info("Successfully put metric data to Cloudwatch!")
    return True


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
    except Exception as inst:
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

    if not hits or not misses:
        logging.info("Cloudwatch metric data empty")
        return 0, 0
    else:
        logging.info("Successfully retrieved and parsed Cloudwatch metric data!")
        return hits[-1], misses[-1]

def get_data_from_cloudwatch(metric_name, period_in_minutes):
    try:
        logging.info("Sending metric get request to Cloudwatch...")
        cloudwatch = boto3.client('cloudwatch', region_name=Config.AWS_REGION)
        graphing_data = cloudwatch.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=period_in_minutes * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName=metric_name,
            Namespace=Config.cloudwatch_namespace,  # Unit='Percent',
            Statistics=['Average'])
        DataList = []
        for item in graphing_data["Datapoints"]:
            Average = item['Average']
            Time = item['Timestamp']
            Data = [Time, Average]
            DataList.append(Data)
        DataList.sort(key=itemgetter(0))

    except Exception:
        logging.info("CloudWatch Metric Query Error - Could not get memcache data from cloudwatch..." + str(inst))
        return None

    times = []
    data = []

    for row in DataList:
        times.append(row[0])
        data.append(row[1])

    stats = list(zip(times, data))

    logging.info("Successfully retrieved and parsed Cloudwatch metric data!")
    return stats

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
        logging.info("CloudWatch Metric Update Error - Could not upload memcache statistics to cloudwatch..." + str((inst)))
        return False

    logging.info("Successfully logged memcache statistics to Cloudwatch!")
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
        cache_sizes = []

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

    except Exception as inst:
        logging.info(
            "CloudWatch Metric Query Error - Could not get memcache statistics to cloudwatch..." + str(inst))
        return None
    return stats

def dynamo_create_image_table():
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName='Images',
            KeySchema=[
                {
                    'AttributeName': 'Bucket',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'Key',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'Bucket',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'Key',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        logging.info("Successfully created Image table!")
        success = True
    except Exception as inst:
        logging.info("Failed to create Image table: " + str(inst))
        success = False

    return success

def dynamo_create_user_table():
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName='UserTable',
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'password',
                    'AttributeType': 'HASH'
                },
                {
                    'AttributeName': 'isEmployee',
                    'AttributeType': 'BOOL'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        logging.info("Successfully created Image table!")
        success = True
    except Exception as inst:
        logging.info("Failed to create Image table: " + str(inst))
        success = False

    return success


def dynamo_add_image(key, bucket):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('Images')
        response = table.put_item(
            Item = {
                'Bucket': bucket,
                'Key': key
            }
        )
        logging.info("Successfully added Image to table!")
        status_code = response['HTTPStatusCode']
    except Exception as inst:
        logging.info("Failed to add Image to table: " + str(inst))
        status_code = 400

    return status_code

def dynamo_add_user(email, password, isEmployee):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('UserTable')
        response = table.put_item(
            Item = {
                'email': email,
                'password': password,
                'isEmployee': isEmployee
            }
        )
        logging.info("Successfully added User to table!")
        status_code = response['HTTPStatusCode']
    except Exception as inst:
        logging.info("Failed to add User to table: " + str(inst))
        status_code = 400

    return status_code

def dynamo_get_user(email):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('UserTable')
        response = table.query(KeyConditionExpression=Key('email').eq(email))
        user = response['Items']
        logging.info("Successfully retrieved user: " + str(user))
    except Exception as inst:
        logging.info("Failed to get User from table: " + str(inst))
        user = []

    return user

def dynamo_get_images(bucket):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('Images')
        response = table.query(KeyConditionExpression=Key('Bucket').eq(bucket))
        images = response['Items']
        logging.info("Successfully retrieved these images: " + str(images))
    except Exception as inst:
        logging.info("Failed to get Images from table: " + str(inst))
        images = []

    return images


def dynamo_delete_images_table():
    try:
        dynamodb = boto3.client('dynamodb')
        dynamodb.delete_table(
            TableName="Images"
        )
        logging.info("Table deleted successfully!")
        success = True
    except Exception as inst:
        logging.info("Failed to delete Images table: " + str(inst))
        success = False

    return success

