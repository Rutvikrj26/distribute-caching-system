import boto3
import logging
from moto import mock_ec2


@mock_ec2
def populate_ec2_instances():
    memapp_instance_ids = []
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        ec2_descriptions = ec2.describe_instances()
        for reservation in ec2_descriptions['Reservations']:
            instance = reservation['Instances']
            instance_id = instance[0]['InstanceId']
            name = instance[0]['Tags'][0]['Value']
            print(instance_id)
            if "memapp" in name:
                logging.info(f'Adding memapp instance with name {name} and ID {instance_id} to master list')
                memapp_instance_ids.append(instance_id)
    except Exception:
        logging.info("FAIL! Could not get a list of ec2 instances on startup.")
        return None
    return memapp_instance_ids


@mock_ec2
def stop_ec2_instance(ec2_instance_ids):
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.stop_instances(InstanceIds=ec2_instance_ids)
        print(response)
    except Exception:
        print("Error!")
        return False
    return True


@mock_ec2
def start_ec2_instance(ec2_instance_ids):
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.start_instances(InstanceIds=ec2_instance_ids)
        print(response)
    except Exception:
        print("Error!")
        return False
    return True


@mock_ec2
def get_ec2_instance_status(ec2_instance_id):
    ec2 = boto3.client('ec2', region_name='us-east-1')
    response = ec2.describe_instance_status(InstanceIds=ec2_instance_id)
    if len(response["InstanceStatuses"]) > 0:
        return response["InstanceStatuses"][0]["InstanceState"]["Name"]
    else:
        return "stopped"
