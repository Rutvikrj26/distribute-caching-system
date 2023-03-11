import requests
import logging
import hashlib
from config import Config
from frontend import frontend
from frontend.models import MemcacheConfig
from manager_app import manager_app, db
from flask import jsonify, request, render_template, flash, redirect, url_for

from manager_app.forms import ManagerConfigForm
from manager_app.models import ManagerConfig
import boto3
import json

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
    "isRandom": 1,
    "maxSize": 2
}
@manager_app.route("/")
@manager_app.route("/index")
def home():
    return render_template('index.html')

# Make a Manager Config Page that provides the options for configuring the pool
# 1. Management Mode Page - Manual Mode/Automatic Mode Selection
# 2. Information for Automatic Mode :
#   Max Miss Rate threshold
#   Min Miss Rate threshold
#   Ratio by which to expand the pool
#   Ratio by which to shrink the pool
# 3. Delete all Application Data Button
# 4. Clear cache Button

@manager_app.route("/config", methods=['GET', 'POST'])
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
        flash("Successfully updated the manager configuration in Database!")

    if current_manager_config.management_mode:  # automatic mode
        form.max_miss_rate_threshold.render_kw = {'disabled': False}
        form.min_miss_rate_threshold.render_kw = {'disabled': False}
        form.expand_pool_ratio.render_kw = {'disabled': False}
        form.shrink_pool_ratio.render_kw = {'disabled': False}

        # TODO : Engage Pool Autoscaler

        return redirect(url_for('config'))

    else:  # manual mode
        form.max_miss_rate_threshold.render_kw = {'disabled': True}
        form.min_miss_rate_threshold.render_kw = {'disabled': True}
        form.expand_pool_ratio.render_kw = {'disabled': True}
        form.shrink_pool_ratio.render_kw = {'disabled': True}

        if form.grow_pool.data:
            if current_manager_config.current_pool_size < 8:
                current_manager_config.current_pool_size += 1
                # TODO : Increase Pool Call Here
                db.session.commit()
                flash(f"Successfully increased pool size to {current_manager_config.current_pool_size}")
            else:
                flash("Pool size already at maximum.")
            return redirect(url_for('config'))

        if form.shrink_pool.data:
            if current_manager_config.current_pool_size > 1:
                current_manager_config.current_pool_size -= 1
                # TODO : Decrease Pool Call Here
                db.session.commit()
                flash(f"Successfully decreased pool size to {current_manager_config.current_pool_size}")
            else:
                flash("Pool size already at minimum.")
            return redirect(url_for('config'))

    return render_template(
        'config.html',
        title="ECE1779 - Group 25 - Configure the manager",
        form=form
    )

# Make a Pool Monitor Page that provides the Folllowing :
# 1. Pool Statistics
#   miss rate : to be pulled from Cloudwatch
#   hit rate : to be pulled from Cloudwatch
#   number of items in cache : To be stored locally in a counter
#   total size of items in cache : To be stored locally in a counter
#   number of requests served per minute : To be pulled from Cloudwtch
#
@manager_app.route("/monitor")
def monitor():

    # Connect to the CloudWatch client
    cloudwatch = boto3.client('cloudwatch')

    # Retrieve the metrics data for the last 30 minutes at 1-minute granularity
    # TODO : Write the code for Metric Calls
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[]
    )

    # Extract the data for each metric

    # Create the data for the circular chart by fetching the required data from database
    active_nodes = manager_app_data["num_active_nodes"]
    inactive_nodes = 8 - active_nodes
    active_nodes_data = [i % active_nodes + 1 for i in range(active_nodes + inactive_nodes)]
    active_nodes_labels = [chr(ord('A') + i % active_nodes) for i in range(active_nodes + inactive_nodes)]

    # Render the template with the data
    return render_template('monitor.html',
                           active_nodes_data=json.dumps(active_nodes_data),
                           active_nodes_labels=json.dumps(active_nodes_labels),
                           miss_rate_data=json.dumps(),
                           hit_rate_data=json.dumps(),
                           num_items_data=json.dumps(),
                           size_items_data=json.dumps(),
                           num_requests_data=json.dumps())



@manager_app.route("/get", methods=['GET', 'POST'])
def get():
    logging.info("Making a GET call")
    key = request.form.get('key')
    logging.info(f"Key received = {key}")
    hashed_key = hashlib.md5(key.encode()).hexdigest().upper()
    num_active_nodes = manager_app_data["num_active_nodes"]
    node_index = int(hashed_key[0], 16) % num_active_nodes
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
        node_index = int(hashed_key[0], 16) % num_active_nodes
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
    node_index = int(hashed_key[0], 16) % num_active_nodes
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
    for i in range(0, Config.MAX_NODES):
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


@manager_app.route("/getNumNodes", methods=['GET', 'POST'])
def get_num_nodes():
    numNodes = manager_app_data['num_active_nodes']
    return jsonify({"status": "success", "status_code": 200, "numNodes": numNodes})
