import os
import boto3
import requests
from operator import itemgetter
from datetime import datetime, timedelta
from urllib.request import Request, urlopen

SITE = os.environ['site']  # URL of the site to check, stored in the site environment variable
EXPECTED = os.environ['expected']  # String expected to be on the page, stored in the expected environment variable
MEMAPP_URL = os.environ['memcache']  # String expected to be on the page, stored in the expected environment variable

AWS_REGION = 'us-east-2'

autoscaler_app_data = {
    'expand_threshold': 0.8,
    'shrink_threshold': 0.2,
    'expand_multiplier': 2.0,
    'shrink_multiplier': 0.5,
    'last_miss_rate': 0.0
}

Config = {
    'cloudwatch_namespace': 'ECE1779/Grp25',
    'misses': 'misses',
    'hits': 'hits',
    'num_items_in_cache': 'number_of_items_in_cache',
    'size_items_in_Megabytes': 'cache_size',
    'num_active_nodes': 'num_active_nodes',
    'num_posts_served': 'posts_served'
}


def get_hits_and_misses_from_cloudwatch(period_in_minutes=1):
    try:
        print("Sending hit/miss get request to Cloudwatch...")
        cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)
        graphing_data_hits = cloudwatch.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=period_in_minutes * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName=Config['hits'],
            Namespace=Config['cloudwatch_namespace'],  # Unit='Percent',
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
            MetricName=Config['misses'],
            Namespace=Config['cloudwatch_namespace'],  # Unit='Percent',
            Statistics=['Sum'])
        MissesList = []
        for item in graphing_data_misses["Datapoints"]:
            Sum = item["Sum"]
            Time = item['Timestamp']
            Misses = [Time, Sum]
            MissesList.append(Misses)
        MissesList.sort(key=itemgetter(0))
    except Exception as inst:
        print("CloudWatch Metric Query Error - Could not get memcache statistics to cloudwatch..." + str(inst))
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
        print("Cloudwatch metric data empty")
        return 0, 0
    else:
        print("Successfully retrieved and parsed Cloudwatch metric data!")
        return hits[-1], misses[-1]


def expand_cache():
    response = requests.get(MEMAPP_URL + "get_cache_capacity")
    jsonResponse = response.json()
    maxSize = int(jsonResponse["cacheSize"])
    if (maxSize < 128):
        if (maxSize == 0):
            new_size = 2
        else:
            new_size = maxSize * 2
        response = requests.post(MEMAPP_URL + "/reconfig", params={'cacheSize': new_size})
        if response.status_code == 200:
            print(f"Memcache configuration auto-updated with maxSize = {new_size}")
        else:
            print("Failed to expand cache")


def shrink_cache():
    response = requests.get(MEMAPP_URL + "get_cache_capacity")
    jsonResponse = response.json()
    maxSize = int(jsonResponse["cacheSize"])
    if (maxSize >= 2):
        new_size = int(maxSize * 0.5)
        response = requests.post(MEMAPP_URL + "/reconfig", params={'cacheSize': new_size})
        if response.status_code == 200:
            print(f"Memcache configuration auto-updated with maxSize = {new_size}")
        else:
            print(f"Failed to shrink cache status code {response}")
    else:
        new_size = 0
        response = requests.post(MEMAPP_URL + "/reconfig", params={'cacheSize': new_size})
        if response.status_code == 200:
            print(f"Memcache configuration auto-updated with maxSize = {new_size}")
        else:
            print("Failed to shrink cache")


def monitor_hit_and_miss_rates():
    # Get hits and misses from Cloudwatch
    hits, misses = get_hits_and_misses_from_cloudwatch()
    print(f"hits = {hits}, misses = {misses}")
    if (hits is None) and (misses is None):
        miss_rate = 0.0
    elif hits + misses == 0:
        miss_rate = 0.0
    else:
        miss_rate = float(misses / (hits + misses))
    print(f"Calculated miss rate as = {miss_rate}")

    last_miss_rate = autoscaler_app_data['last_miss_rate']
    autoscaler_app_data['last_miss_rate'] = miss_rate

    if miss_rate > autoscaler_app_data['expand_threshold'] and miss_rate >= last_miss_rate:
        expand_cache()
    elif miss_rate < autoscaler_app_data['shrink_threshold'] and miss_rate <= last_miss_rate:
        shrink_cache()


def validate(res):
    '''Return False to trigger the canary

    Currently this simply checks whether the EXPECTED string is present.
    However, you could modify this to perform any number of arbitrary
    checks on the contents of SITE.
    '''
    return EXPECTED in res


def lambda_handler(event, context):
    print('Checking {} at {}...'.format(SITE, event['time']))
    try:
        req = Request(SITE, headers={'User-Agent': 'AWS Lambda'})
        if not validate(str(urlopen(req).read())):
            raise Exception('Validation failed')
    except:
        print('Check failed!')
        raise
    else:
        print('Check passed!')
        return event['time']
    finally:
        print('Check complete at {}'.format(str(datetime.now())))
        monitor_hit_and_miss_rates()