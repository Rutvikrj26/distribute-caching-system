import sys

from memapp import memapp, memcache, policy
from flask import jsonify, request
import threading
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import time
from sqlalchemy import create_engine
from memapp.models import MemcacheData
import logging
from frontend import frontend
from frontend.models import MemcacheConfig
from config import Config

# Logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Connecting to the database
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Local Memcache Stats Data
memcache_data = {
    "timestamp": None,
    "hits": 0,
    "misses": 0,
    "posts_served": 0,
    "cache_size": 0,
    "isRandom": 1,
    "max_size": 2,
    "commits_running": False
}


@memapp.route("/", methods=['GET'])
def index():
    return jsonify({"status": "success", "status_code": 200})


@memapp.route("/get", methods=['GET', 'POST'])
def get():
    logging.info("Making a GET call")
    key = request.form.get('key')
    logging.info(f"Key received = {key}")

    if key in memcache:
        logging.info(f"Image found in cache with key = {key}")
        memcache.move_to_end(key)
        memcache_data["hits"] += 1
        return jsonify({"status": "success", "value": memcache[key], "status_code": 200})
    else:
        memcache_data["misses"] += 1
        return jsonify({"status": "failure", "message": "Image not in cache", "status_code": 404})


@memapp.route("/put", methods=['POST'])
def put():
    logging.info("Making a PUT call")
    key = request.form['key']
    value = request.form['value']
    logging.info(f"Data received with key = {key}")
    logging.info(f"Value received with value length = {len(value)}")

    # inserting the data into Cache   
    if key is not None and value is not None:
        if memcache_data["isRandom"] == 1:
            fits_in_cache, memcache_data["cache_size"] = policy.random_replacement(memcache, memcache_data["cache_size"], memcache_data["max_size"], key, value)
        else:
            fits_in_cache, memcache_data["cache_size"] = policy.lru_replacement(memcache, memcache_data["cache_size"], memcache_data["max_size"], key, value)
        # Check if image was too big for cache
        if fits_in_cache:
            memcache_data["posts_served"] += 1
            logging.info(f"Successfully stored value with key = {key} in cache")
            return jsonify({"status": "success", "status_code": 200})
        else:
            logging.info(f"Value with key = {key} too big for cache!")
            return jsonify({"status": "too_big", "status_code": 201})
    else:
        logging.info("FAIL!!! Either key or value are invalid. See above for cause.")
        return jsonify({"status": "Fail", "Error": "Either Key or Value Empty", "status_code": 500})


@memapp.route("/get_all_keys", methods=['GET', 'POST'])
def get_all_keys():
    logging.info("Getting all keys currently in memcache...")
    all_keys = list(memcache.keys())
    logging.info(f"Keys are: {all_keys}")
    return jsonify({"status": "success", "keys": all_keys, "status_code": 200})


@memapp.route("/invalidate_key", methods=['GET', 'POST'])
def invalidate_key():
    logging.info("Invalidating a key...")
    key = request.form['key']
    if key in memcache:
        size_of_value = round(sys.getsizeof(memcache[key]) / (1024 * 1024), 5)
        memcache_data["cache_size"] -= size_of_value
        del memcache[key]
        logging.info("Key found in cache, invalidated.")
    else:
        logging.info("No key found in cache. No action taken.")
    return jsonify({"status": "success", "status_code": 200})


@memapp.route("/clearcache", methods=["GET", "POST"])
def clearcache():
    logging.info("Attempting to clear cache...")
    memcache.clear()
    memcache_data["cache_size"] = 0
    logging.info("Successfully cleared cache")
    return jsonify({"status": "success", "status_code": 200})


def commit_update():
    while True:
        logging.info("Starting 5 second sleep timer...")
        logging.info(f"isRandom = {memcache_data['isRandom']}, max_size = {memcache_data['max_size']}")
        time.sleep(5)

        # First update memcache data
        with memapp.app_context():
            logging.info("Logging data to database...")
            memcache_data["timestamp"] = datetime.utcnow()
            new_entry = MemcacheData(timestamp=memcache_data['timestamp'], hits=memcache_data['hits'],
                                     misses=memcache_data['misses'], posts_served=memcache_data['posts_served'],
                                     num_items=len(memcache), current_size=memcache_data["cache_size"])
            session.add(new_entry)
            session.commit()
            logging.info("UPDATE: refreshed database with new memcache data")


@memapp.route('/update_db', methods=['POST'])
def update():
    logging.info("Request received to start logging to database...")
    thread = threading.Thread(target=commit_update)
    if memcache_data["commits_running"]:
        logging.info("Commit thread already running!")
        return jsonify({"status": "fail", "status_code": 400})
    thread.start()
    memcache_data["commits_running"] = True
    logging.info("Logging thread started successfully...")
    return jsonify({"status": "success", "status_code": 200})


# Refresh Configuration by querying it from the database
@memapp.route('/refresh_config', methods=['POST'])
def refresh_configuration():
    logging.info("Updating configuration...")
    memcache_data["isRandom"] = int(request.form['isRandom'])
    memcache_data["max_size"] = int(request.form['max_size'])

    # Resize the cache if we shrink it and need to evict items
    if memcache_data["max_size"] < memcache_data["cache_size"]:
        if memcache_data["isRandom"] == 1:
            logging.info("Cache Resizing Required : Updating the current cache based on Random Replacement Policy")
            memcache_data["cache_size"] = policy.random_resize(memcache, memcache_data["cache_size"], memcache_data["max_size"])
        else:
            logging.info("Cache Resizing Required : Updating the current cache based on LRU Replacement Policy")
            memcache_data["cache_size"] = policy.lru_resize(memcache, memcache_data["cache_size"], memcache_data["max_size"])

    return jsonify({"status": "success", "status_code": 200})
