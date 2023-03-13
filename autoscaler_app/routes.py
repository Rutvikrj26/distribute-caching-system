import time
import hashlib
import logging
import requests
import threading
import aws_helper
from datetime import datetime
from flask import request, jsonify
from config import Config
from autoscaler_app import autoscaler_app

logger = logging.getLogger()
logger.setLevel(logging.INFO)

memapp_urls = [
    Config.MEMAPP_0_URL,
    Config.MEMAPP_1_URL,
    Config.MEMAPP_2_URL,
    Config.MEMAPP_3_URL,
    Config.MEMAPP_4_URL,
    Config.MEMAPP_5_URL,
    Config.MEMAPP_6_URL,
    Config.MEMAPP_7_URL,
]

autoscaler_app_data = {
    'num_active_nodes': 1,
    'automatic': 1,
    'expand_threshold': 0.8,
    'shrink_threshold': 0.2,
    'expand_multiplier': 2.0,
    'shrink_multiplier': 0.5,
    'last_miss_rate': 0.0,
    'monitoring': False
}


@autoscaler_app.route('/configure_autoscaler', methods=['GET', 'POST'])
def configure_autoscaler():
    try:
        logging.info(request.form)
        if request.form['expand_threshold'] != "None":
            autoscaler_app_data['expand_threshold'] = float(request.form['expand_threshold'])
        if request.form['shrink_threshold'] != "None":
            autoscaler_app_data['shrink_threshold'] = float(request.form['shrink_threshold'])
        if request.form['expand_multiplier'] != "None":
            autoscaler_app_data['expand_multiplier'] = float(request.form['expand_multiplier'])
        if request.form['shrink_multiplier'] != "None":
            autoscaler_app_data['shrink_multiplier'] = float(request.form['shrink_multiplier'])
        if request.form['mode'] != "None":
            autoscaler_app_data['automatic'] = int(request.form['mode'])

        if autoscaler_app_data['automatic'] == 0:
            if request.form['numNodes'] != "None":
                manual_num_nodes = int(request.form['numNodes'])
            else:
                manual_num_nodes = autoscaler_app_data['num_active_nodes']
            node_delta = manual_num_nodes - autoscaler_app_data['num_active_nodes']
            if node_delta < 0:
                shrink_node_pool(manual=True, node_delta=abs(node_delta))
            elif node_delta > 0:
                expand_node_pool(manual=True, node_delta=node_delta)
    except Exception as inst:
        logging.info("ERROR! Could not configure autoscaler. Was request formatted properly??" + str(inst))
        return jsonify({"status": "failure", "status_code": 400})
    logging.info("Success! Autoscaler successfully reconfigured.")
    return jsonify({"status": "success", "status_code": 200})


def monitor_hit_and_miss_rates():
    while True:
        logging.info("Starting 60 second sleep timer...")
        time.sleep(60)

        # Get hits and misses from Cloudwatch
        hits, misses = aws_helper.get_hits_and_misses_from_cloudwatch()
        if hits + misses == 0:
            miss_rate = 0.0
        else:
            miss_rate = float(misses / (hits + misses))

        last_miss_rate = autoscaler_app_data['last_miss_rate']
        autoscaler_app_data['last_miss_rate'] = miss_rate

        if autoscaler_app_data['automatic'] == 1:
            if miss_rate > autoscaler_app_data['expand_threshold'] and miss_rate > last_miss_rate:
                if autoscaler_app_data['num_active_nodes'] < Config.MAX_NODES:
                    expand_node_pool()
            elif miss_rate < autoscaler_app_data['shrink_threshold'] and miss_rate < last_miss_rate:
                if autoscaler_app_data['num_active_nodes'] > 1:
                    shrink_node_pool()

        # While we're threading, put num_active_nodes to Cloudwatch
        aws_helper.put_data_to_cloudwatch(Config.num_active_nodes, autoscaler_app_data['num_active_nodes'],
                                                  datetime.utcnow(), unit=None)


def expand_node_pool(manual=False, node_delta=0):
    # First we call back all key/value pairs to be redistributed
    key_value_dict = get_all_key_value_pairs_from_nodes()
    old_active_nodes = autoscaler_app_data['num_active_nodes']
    # Next grow node pool according to multiplier
    if manual:
        autoscaler_app_data['num_active_nodes'] += node_delta
    else:
        autoscaler_app_data['num_active_nodes'] = min(int(autoscaler_app_data['num_active_nodes'] * autoscaler_app_data['expand_multiplier']), Config.MAX_NODES)
    new_active_nodes = autoscaler_app_data['num_active_nodes']

    # Write back keys to bigger node pool
    for key in key_value_dict.keys():
        value = key_value_dict[key]
        hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
        num_active_nodes = autoscaler_app_data["num_active_nodes"]
        node_index = int(hashed_key[0], 16) % num_active_nodes
        logging.info(f"Sending key and value to node at index = {node_index}")
        response = requests.post(memapp_urls[node_index] + "/put", data={'key': key, 'value': value})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info(f"Successfully stored value with key = {key} in cache node at index = {node_index}")
        elif jsonResponse["status"] == "too_big":
            logging.info(f"Value with key = {key} too big for node at index = {node_index}")
        else:
            logging.info("FAIL!!! Received non-200 response from cache node")

    # Send num_active_node update to frontend
    requests.post(Config.FRONTEND_URL + "update_num_active_nodes",
                  data={'old_active_nodes': old_active_nodes, 'new_active_nodes': new_active_nodes})
    # Send num_active_node update to manager_app
    requests.post(Config.MANAGER_APP_URL + "update_num_active_nodes",
                  data={'numNodes': new_active_nodes})


def shrink_node_pool(manual=False, node_delta=0):
    # First we call back all key/value pairs to be redistributed
    key_value_dict = get_all_key_value_pairs_from_nodes()
    old_active_nodes = autoscaler_app_data['num_active_nodes']
    # Next shrink node pool according to multiplier
    if manual:
        autoscaler_app_data['num_active_nodes'] -= node_delta
    else:
        autoscaler_app_data['num_active_nodes'] = max(int(autoscaler_app_data['num_active_nodes'] * autoscaler_app_data['shrink_multiplier']), 1)
    new_active_nodes = autoscaler_app_data['num_active_nodes']

    # Write back keys to smaller node pool
    for key in key_value_dict.keys():
        value = key_value_dict[key]
        hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
        num_active_nodes = autoscaler_app_data["num_active_nodes"]
        node_index = int(hashed_key[0], 16) % num_active_nodes
        logging.info(f"Sending key and value to node at index = {node_index}")
        response = requests.post(memapp_urls[node_index] + "/put", data={'key': key, 'value': value})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info(f"Successfully stored value with key = {key} in cache node at index = {node_index}")
        elif jsonResponse["status"] == "too_big":
            logging.info(f"Value with key = {key} too big for node at index = {node_index}")
        else:
            logging.info("FAIL!!! Received non-200 response from cache node")

    # Send num_active_node update to frontend
    requests.post(Config.FRONTEND_URL + "update_num_active_nodes",
                  data={'old_active_nodes': old_active_nodes, 'new_active_nodes': new_active_nodes})
    # Send num_active_node update to manager_app
    requests.post(Config.MANAGER_APP_URL + "update_num_active_nodes",
                  data={'numNodes': new_active_nodes})


def get_all_key_value_pairs_from_nodes():
    key_value_dict = {}
    for i in range(0, autoscaler_app_data['num_active_nodes']):
        logging.info(f"Getting key/value pairs from cache node {i}")
        response = requests.post(memapp_urls[i] + "return_values")
        jsonResponse = response.json()
        if jsonResponse['status_code'] == 200:
            logging.info(f"Received key/value pairs from cache node {i}")
            node_dict = jsonResponse['value']
            key_value_dict.update(node_dict)
        else:
            logging.info(f"ERROR! Failed to get key/value pairs from cache node {i}")
        response = requests.post(memapp_urls[i] + "clearcache")
        jsonResponse = response.json()
        if jsonResponse['status_code'] == 200:
            logging.info(f"Successfully cleared cache node {i}")
        else:
            logging.info(f"ERROR! Failed to clear cache node {i}...")
    logging.info(f"Received all key/value pairs from active cache nodes...")
    return key_value_dict


def start_monitoring():
    logging.info("Attempting to start autoscaler monitoring...")
    thread = threading.Thread(target=monitor_hit_and_miss_rates)
    if autoscaler_app_data["monitoring"]:
        logging.info("Monitoring thread already running!")
    else:
        thread.start()
        autoscaler_app_data["monitoring"] = True
        logging.info("Monitoring thread started successfully!")


@autoscaler_app.route("/getNumNodes", methods=['GET', 'POST'])
def get_num_nodes():
    numNodes = autoscaler_app_data['num_active_nodes']
    return jsonify({"status": "success", "status_code": 200, "numNodes": numNodes})
