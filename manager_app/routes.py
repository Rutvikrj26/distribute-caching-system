import time
import requests
import logging
import hashlib
import threading
from config import Config
from frontend import frontend
from frontend.models import MemcacheConfig
from manager_app import manager_app, db
from manager_app.models import ManagerConfig
from flask import jsonify, request, render_template, flash, redirect, url_for

from manager_app.forms import ManagerConfigForm
from manager_app.models import ManagerConfig

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

manager_app_data = {
    "num_active_nodes": 1,
    "monitoring": False,
    "hit_rate": 1.0,
    "miss_rate": 0.0,
    "last_miss_rate": 0.0,
    "expand_threshold": 0.8,
    "shrink_threshold": 0.2,
    "expand_multiplier": 2.0,
    "shrink_multiplier": 0.5,
    "automatic": 1,
    "isRandom": 1,
    "maxSize": 2
}
@manager_app.route("/")
@manager_app.route("/home")
def home():
    return render_template('home.html', title="ECE1779 - Group 25 - Gauri Billore, Joseph Longpre, Rutvik Solanki")

# Make a Manager Config Page that provides the options for configuring the pool
# 1. Management Mode Page - Manual Mode/Automatic Mode Selection
# 2. Information for Automatic Mode :
#   Max Miss Rate threshold
#   Min Miss Rate threshold
#   Ratio by which to expand the pool
#   Ratio by which to shrink the pool
# 3. Delete all Application Data Button
# 4. Clear cache Button
@manager_app.route("/config")
def config():
    logging.info("Accessed MANAGER CONFIGURATION page")
    with manager_app.app_context():
        current_manager_config = ManagerConfig.query.first()
        logging.info(f"Management Mode = {current_manager_config.management_mode}")
    form = ManagerConfigForm(
        management_mode=current_manager_config.management_mode,
        max_miss_rate_threshold=current_manager_config.max_miss_rate_threshold,
        min_miss_rate_threshold=current_manager_config.min_miss_rate_threshold,
        expand_pool_ratio=current_manager_config.expand_pool_ratio,
        shrink_pool_ratio=current_manager_config.shrink_pool_ratio
    )
    if form.validate_on_submit():
        with manager_app.app_context():
            current_manager_config = ManagerConfig.query.first()
            current_manager_config.management_mode = form.management_mode.data
            current_manager_config.max_miss_rate_threshold = form.max_miss_rate_threshold.data
            current_manager_config.min_miss_rate_threshold = form.min_miss_rate_threshold.data
            current_manager_config.expand_pool_ratio = form.expand_pool_ratio.data
            current_manager_config.shrink_pool_ratio = form.shrink_pool_ratio.data
            db.session.commit()
        flash("Successfully updated the manager configuration!")

        # TODO : Update the Pool Statistics based on the Updated Pool Configuration.

        return redirect(url_for('config'))
    return render_template(
        'config.html',
        title="ECE1779 - Group 25 - Configure the manager",
        form=form
    )



# Make a Pool Monitor Page that provides the Folllowing :
# 1. Pool Statistics
#   miss rate,
#   hit rate,
#   number of items in cache,
#   total size of items in cache,
#   number of requests served per minute.
# 2. Active Nodes & Aggregate information Charts for all the Pools.
@manager_app.route("/monitor")
def monitor():



    return render_template('monitor.html')
@manager_app.route("/get", methods=['GET', 'POST'])
def get():
    logging.info("Making a GET call")
    key = request.form.get('key')
    logging.info(f"Key received = {key}")
    hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
    num_active_nodes = manager_app_data["num_active_nodes"]
    node_index = int(hashed_key[0], num_active_nodes) % num_active_nodes
    logging.info(f"Querying memory node at node_index = {node_index}")
    response = requests.post(memapp_urls[node_index]+"/get", data={'key': key})
    jsonResponse = response.json()
    if jsonResponse["status_code"] == 200:
        logging.info("Image found in cache, accessing...")
        b64string = jsonResponse['value']
        return jsonify({"status": "success", "value": b64string, "status_code": 200})
    else:
        logging.info("Image not in cache, cache miss should be recorded...")
        return jsonify({"status": "failure", "message": "Image not in cache", "status_code": 404})


@manager_app.route("/put", methods=['POST'])
def put():
    logging.info("Making a PUT call")
    key = request.form['key']
    value = request.form['value']
    logging.info(f"Data received with key = {key}")
    logging.info(f"Value received with value length = {len(value)}")
    # inserting the data into Cache
    if key is not None and value is not None:
        hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
        num_active_nodes = manager_app_data["num_active_nodes"]
        node_index = int(hashed_key[0], num_active_nodes) % num_active_nodes
        logging.info(f"Sending key and value to node at index = {node_index}")
        response = requests.post(memapp_urls[node_index] + "/put", data={'key': key, 'value': value})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info(f"Successfully stored value with key = {key} in cache node at index = {node_index}")
            return jsonify({"status": "success", "status_code": 200})
        elif jsonResponse["status"] == "too_big":
            logging.info(f"Value with key = {key} too big for node at index = {node_index}")
            return jsonify({"status": "too_big", "status_code": 201})
        else:
            logging.info("FAIL!!! Received non-200 response from cache node")
            return jsonify({"status": "Fail", "Error": "Either Key or Value Empty", "status_code": 500})
    else:
        logging.info("FAIL!!! Either key or value are invalid. See above for cause.")
        return jsonify({"status": "Fail", "Error": "Either Key or Value Empty", "status_code": 500})


@manager_app.route("/invalidate_key", methods=['GET', 'POST'])
def invalidate_key():
    logging.info("Invalidating a key...")
    key = request.form['key']
    hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
    num_active_nodes = manager_app_data["num_active_nodes"]
    node_index = int(hashed_key[0], num_active_nodes) % num_active_nodes
    logging.info(f"Invalidating key at node: {node_index}")
    response = requests.post(memapp_urls[node_index] + "/invalidate_key", data={'key': key})
    jsonResponse = response.json()
    if jsonResponse["status_code"] != 200:
        logging.info(f"ERROR! Node at index {node_index} returned invalid response when invalidating key...")
        return jsonify({"status": "failure", "status_code": 400})
    else:
        return jsonify({"status": "success", "status_code": 200})


@manager_app.route("/get_all_keys", methods=['GET', 'POST'])
def get_all_keys():
    logging.info("Getting all keys currently in memcache nodes...")
    all_keys = []
    for i in range(0, manager_app_data["num_active_nodes"]):
        response = requests.post(memapp_urls[i] + "/get_all_keys")
        jsonResponse = response.json()
        keys = jsonResponse["keys"]
        all_keys = all_keys + keys
    logging.info(f"Keys are: {all_keys}")
    return jsonify({"status": "success", "keys": all_keys, "status_code": 200})


@manager_app.route("/clearcache", methods=["GET", "POST"])
def clearcache():
    logging.info("Attempting to clear cache for all nodes...")
    for i in range(0, manager_app_data["num_active_nodes"]):
        requests.post(memapp_urls[i] + "/clearcache")
    logging.info("Successfully cleared cache for all active nodes!")
    return jsonify({"status": "success", "status_code": 200})


@manager_app.route('/refresh_config', methods=['POST'])
def refresh_configuration():
    with frontend.app_context():
        logging.info("Updating configuration information...")
        memcache_config_data = MemcacheConfig.query.first()
        assert(memcache_config_data is not None)
        manager_app_data["isRandom"] = memcache_config_data.isRandom
        manager_app_data["max_size"] = memcache_config_data.maxSize

    # Forward fresh configuration data to ALL nodes, active or otherwise
    for i in range(0, Config.MAX_NODES):
        response = requests.post(memapp_urls[i] + "/refresh_config", data={'isRandom': manager_app_data["isRandom"], 'max_size': manager_app_data["max_size"]})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info(f"Successfully refreshed memcache_config on node {i}!")
        else:
            logging.info(f"ERROR! Node {i} failed to refresh its configuration...")

    return jsonify({"status": "success", "status_code": 200})


@manager_app.route("/update_statistics", methods=['GET', 'POST'])
def update_statistics():
    # TODO: Pass information from frontend webpage about automatic/manual mode, grow/shrink multipliers, etc.
    # TODO: Will probably have our manual updates here as well
    pass


@manager_app.route('/update_db', methods=['POST'])
def update():
    logging.info("Request received for manager_app to query Cloudwatch for automated cache changes...")
    thread = threading.Thread(target=monitor_hit_and_miss_rates)
    if manager_app_data["monitoring"]:
        logging.info("The manager_app is already monitoring Cloudwatch!")
        return jsonify({"status": "fail", "status_code": 400})
    thread.start()
    manager_app_data["monitoring"] = True
    logging.info("Monitoring thread for Cloudwatch in manager_app started successfully...")
    return jsonify({"status": "success", "status_code": 200})


@manager_app.route("/getNumNodes", methods=['GET', 'POST'])
def get_num_nodes():
    numNodes = manager_app_data['num_active_nodes']
    return jsonify({"status": "success", "status_code": 200, "numNodes": numNodes})


def monitor_hit_and_miss_rates():
    while True:
        logging.info("Starting 5 second sleep timer...")
        logging.info(f"Miss rate = {manager_app_data['miss_rate']}, hit_rate = {manager_app_data['hit_rate']}, last_miss_rate = {manager_app_data['last_miss_rate']}")
        time.sleep(5)

        # TODO: Get hit_rate and miss_rate metrics from Cloudwatch... dummy values below
        miss_rate = 0.5
        hit_rate = 0.5

        manager_app_data['last_miss_rate'] = manager_app_data['miss_rate']
        manager_app_data['miss_rate'] = miss_rate
        manager_app_data['hit_rate'] = hit_rate

        if manager_app_data['automatic'] == 1:
            if miss_rate > manager_app_data['expand_threshold'] and miss_rate > manager_app_data['last_miss_rate']:
                if manager_app_data['num_active_nodes'] < Config.MAX_NODES:
                    expand_node_pool()
            elif miss_rate < manager_app_data['shrink_threshold'] and miss_rate < manager_app_data['last_miss_rate']:
                if manager_app_data['num_active_nodes'] > 1:
                    shrink_node_pool()


def expand_node_pool(manual=False):
    # First we call back all key/value pairs to be redistributed
    key_value_dict = get_all_key_value_pairs_from_nodes()
    # Next grow node pool according to multiplier
    if manual:
        manager_app_data['num_active_nodes'] += 1
    else:
        manager_app_data['num_active_nodes'] = min(int(manager_app_data['num_active_nodes'] * manager_app_data['expand_multiplier']), Config.MAX_NODES)
    # Write back keys to smaller node pool
    for key in key_value_dict.keys():
        value = key_value_dict[key]
        hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
        num_active_nodes = manager_app_data["num_active_nodes"]
        node_index = int(hashed_key[0], num_active_nodes) % num_active_nodes
        logging.info(f"Sending key and value to node at index = {node_index}")
        response = requests.post(memapp_urls[node_index] + "/put", data={'key': key, 'value': value})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info(f"Successfully stored value with key = {key} in cache node at index = {node_index}")
        elif jsonResponse["status"] == "too_big":
            logging.info(f"Value with key = {key} too big for node at index = {node_index}")
        else:
            logging.info("FAIL!!! Received non-200 response from cache node")


def shrink_node_pool(manual=False):
    # First we call back all key/value pairs to be redistributed
    key_value_dict = get_all_key_value_pairs_from_nodes()
    # Next shrink node pool according to multiplier
    if manual:
        manager_app_data['num_active_nodes'] -= 1
    else:
        manager_app_data['num_active_nodes'] = max(int(manager_app_data['num_active_nodes'] * manager_app_data['shrink_multiplier']), 1)
    # Write back keys to smaller node pool
    for key in key_value_dict.keys():
        value = key_value_dict[key]
        hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
        num_active_nodes = manager_app_data["num_active_nodes"]
        node_index = int(hashed_key[0], num_active_nodes) % num_active_nodes
        logging.info(f"Sending key and value to node at index = {node_index}")
        response = requests.post(memapp_urls[node_index] + "/put", data={'key': key, 'value': value})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info(f"Successfully stored value with key = {key} in cache node at index = {node_index}")
        elif jsonResponse["status"] == "too_big":
            logging.info(f"Value with key = {key} too big for node at index = {node_index}")
        else:
            logging.info("FAIL!!! Received non-200 response from cache node")


def get_all_key_value_pairs_from_nodes():
    key_value_dict = {}
    for i in range(0, manager_app_data['num_active_nodes']):
        logging.info(f"Getting key/value pairs from cache node {i}")
        # TODO: Need to write this function in memapp/routes.py
        response = requests.post(memapp_urls[i] + "/return_values_and_clear")
        jsonResponse = response.json()
        if jsonResponse['status_code'] == 200:
            logging.info(f"Received key/value pairs from cache node {i}")
            node_dict = jsonResponse['value']
            key_value_dict.update(node_dict)
    logging.info(f"Received all key/value pairs from active cache nodes...")
    return key_value_dict
