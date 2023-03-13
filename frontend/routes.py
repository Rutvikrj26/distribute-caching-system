import logging
import requests
import aws_helper
from config import Config
from base64 import b64encode
from frontend.models import Image
from frontend import frontend, db
from memapp import memapp
from flask import render_template, redirect, url_for, request, flash, jsonify
from frontend.forms import SubmitButton, UploadForm, DisplayForm

logger = logging.getLogger()
logger.setLevel(logging.INFO)

frontend_data = {
    "update_active_nodes": False,
    "old_active_nodes": 1,
    "new_active_nodes": 1,
    "commits_running": False
}


@frontend.route('/')
@frontend.route('/index')
def index():
    if frontend_data['update_active_nodes']:
        frontend_data['update_active_nodes'] = False
        flash(f'SIZE OF CACHE POOL HAS CHANGED: from {frontend_data["old_active_nodes"]} to {frontend_data["new_active_nodes"]}')
    return render_template('index.html', title="ECE1779 - Group 25 - Gauri Billore, Joseph Longpre, Rutvik Solanki")


@frontend.route('/upload', methods=['GET', 'POST'])
def upload():
    logging.info("Accessed UPLOAD page")
    form = UploadForm()
    if form.validate_on_submit():
        key = form.key.data
        file = form.value.data

        # Check if the file type is valid
        if file.filename.split(".")[-1].strip() not in Config.ALLOWED_EXTENSIONS:
            flash("File type is not allowed - please upload a PNG, JPEG, JPG, or GIF file.")
            return redirect(url_for('upload'))

        b64string = b64encode(file.read()).decode("ASCII")

        # Store on S3
        response = requests.post(Config.S3_APP_URL + "upload_image",
                                 data={'key': key, 'value': b64string, 'bucket': Config.S3_BUCKET_NAME})
        jsonResponse = response.json()
        if jsonResponse['status_code'] != 200:
            logging.info("FAIL!!! Could not save image to S3")
            flash("ERROR: Could not save the image to S3. Please try again later.")
            return redirect(url_for('upload'))
        logging.info("Successfully saved image to S3!")
        flash("Image successfully uploaded!")

        # Store in database
        try:
            with frontend.app_context():
                # First, see if key already in database
                image = Image.query.filter_by(id=key).first()
                if image:
                    db.session.delete(image)
                    db.session.commit()
                image = Image(id=key, value=Config.S3_BUCKET_NAME)
                db.session.add(image)
                db.session.commit()
                logging.info("Successfully saved image to database")
        except Exception:
            logging.info("FAIL!!! Could not save image to database")
            flash("ERROR: Could not upload the image to the database.")
            return redirect(url_for('upload'))

        # Invalidate key in cache
        requests.post(Config.MANAGER_APP_URL + "/invalidate_key", data={'key': key})

        # Store in cache
        try:
            response = requests.post(Config.MANAGER_APP_URL + "/put", data={'key': key, 'value': b64string})
            jsonResponse = response.json()
            if jsonResponse["status_code"] == 200:
                logging.info("Successfully uploaded image to cache")
            else:
                logging.info("FAIL!!! Received non-200 response from cache manager")
                flash("ERROR: Bad response from cache.")
            return redirect(url_for('upload'))
        except Exception:
            logging.info("FAIL!!! Error encoding file or sending encoded file to cache.")
            flash("ERROR: Could not store image in cache...")
            return redirect(url_for('upload'))

    if frontend_data['update_active_nodes']:
        frontend_data['update_active_nodes'] = False
        flash(f'SIZE OF CACHE POOL HAS CHANGED: from {frontend_data["old_active_nodes"]} to {frontend_data["new_active_nodes"]}')
    return render_template('upload.html', title="ECE1779 - Group 25 - Upload a Key-Value Pair", form=form)


@frontend.route('/display', methods=['GET', 'POST'])
def display():
    logging.info("Accessed DISPLAY page")
    form = DisplayForm()
    if form.validate_on_submit():
        # Get form data
        key = form.key.data

        # Try cache first
        logging.info("Trying cache first...")
        response = requests.post(Config.MANAGER_APP_URL + "/get", data={'key': key})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info("Image found in cache, accessing...")
            b64string = jsonResponse['value']
            logging.info("Image retrieved from cache...")
            image_location = 'data:image/png;base64,' + b64string

        # Else, go to database for S3 lookup
        else:
            logging.info("Image NOT in cache, going to disk...")
            image = Image.query.filter_by(id=key).first()
            if image is None:
                logging.info("FAIL!!! Image not in cache or on disk - BAD KEY")
                flash("Could not find an image associated with this key.")
                return redirect(url_for('display'))
            else:
                logging.info("Image found on disk...")
                bucket = image.value
            logging.info(f"Putting image with key = {key} into cache")
            response = requests.post(Config.S3_APP_URL + "download_image",
                                     data={'key': key, 'bucket': bucket})
            jsonResponse = response.json()
            if jsonResponse['status_code'] != 200:
                logging.info("FAIL!!! Could not return the image to cache - S3 failure")
                flash("ERROR: Could not receive fileobj from S3...")
                return redirect(url_for('display'))
            b64string = jsonResponse['value']
            image_location = 'data:image/png;base64,' + b64string

            # Now need to store back in the cache!
            logging.info(f"Successfully retrieved b64string from s3_app for key = {key}")
            response = requests.post(Config.MANAGER_APP_URL + "/put", data={'key': key, 'value': b64string})
            jsonResponse = response.json()
            if jsonResponse["status_code"] == 200:
                logging.info("Successfully uploaded image to cache")
            else:
                logging.info("FAIL!!! Could not store image back into cache!")
                flash("WARNING! Image is too big for the cache...")

        # Now show image to user
        flash(f"Showing image for key = {key}")
        if frontend_data['update_active_nodes']:
            frontend_data['update_active_nodes'] = False
            flash(f'SIZE OF CACHE POOL HAS CHANGED: from {frontend_data["old_active_nodes"]} to {frontend_data["new_active_nodes"]}')
        return render_template('display.html', title="ECE1779 - Group 25 - Display an Image", form=form,
                               image_location=image_location)

    if frontend_data['update_active_nodes']:
        frontend_data['update_active_nodes'] = False
        flash(f'SIZE OF CACHE POOL HAS CHANGED: from {frontend_data["old_active_nodes"]} to {frontend_data["new_active_nodes"]}')
    return render_template('display.html', title="ECE1779 - Group 25 - Display an Image",
                           form=form, image_location=None)


@frontend.route('/show_delete_keys', methods=['GET', 'POST'])
def show_delete_keys():
    logging.info("Accessed DELETE KEYS page")
    form = SubmitButton()
    images = Image.query.order_by(Image.timestamp.asc())
    if form.validate_on_submit():
        # First delete from database:
        try:
            for image in images:
                db.session.delete(image)
            db.session.commit()
            logging.info("Successfully deleted key/image pairs from database")
        except Exception:
            logging.info("FAIL!!! Could not delete key/image pairs from database")
            flash("WARNING: Could not delete key/image pairs from database")

        # Next, delete from disk:
        response = requests.post(Config.S3_APP_URL + "delete_all")
        jsonResponse = response.json()
        if jsonResponse['status_code'] != 200:
            logging.info("FAIL!!! Could not delete key/image pairs from S3")
            flash("WARNING: Could not delete key/image pairs from S3...")

        # Last, delete from cache
        try:
            response = requests.post(Config.MANAGER_APP_URL + 'clearcache')
            if response.status_code == 200:
                logging.info("Successfully deleted key/image pairs from cache")
            else:
                logging.info("FAIL!!! Could not delete key/image pairs from cache")
                flash("WARNING: Could not delete key/image pairs from cache")
        except Exception:
            logging.info("FAIL!!! Could not delete key/image pairs from cache")
            flash("WARNING: Could not delete key/image pairs from cache")

        # Issue success
        logging.info("Successfully deleted key/image pairs from database, disk, and cache")
        flash("All keys successfully deleted from cache, database, and disk.")
        return redirect(url_for('show_delete_keys'))

    if frontend_data['update_active_nodes']:
        frontend_data['update_active_nodes'] = False
        flash(f'SIZE OF CACHE POOL HAS CHANGED: from {frontend_data["old_active_nodes"]} to {frontend_data["new_active_nodes"]}')
    return render_template('show_delete_keys.html', title="ECE1779 - Group 25 - Show and Delete All Keys",
                           form=form, images=images)


# # TODO: I think this gets deleted and replaced with the UI from manager_app??
# @frontend.route('/memcache_stats', methods=['GET'])
# def memcache_stats():
#     logging.info("Accessed MEMCACHE STATISTICS page")
#
#     # First get current memcache configuration
#     current_memcache_config = MemcacheConfig.query.filter_by(id=1).first()
#     current_policy = "Random Replacement" if current_memcache_config.isRandom == 1 else "Least Recently Used"
#     max_size = current_memcache_config.maxSize
#
#     # Next get memcache statistics, populated by memcache
#     with memapp.app_context():
#         memcache_data = MemcacheData.query.order_by(MemcacheData.timestamp.desc()).first()
#         num_items = memcache_data.num_items
#         current_size = memcache_data.current_size
#         posts_served = memcache_data.posts_served
#         gets_served = memcache_data.misses + memcache_data.hits
#         miss_rate = 0 if (gets_served == 0) else (memcache_data.misses * 100 / gets_served)
#         hit_rate = 0 if (gets_served == 0) else (memcache_data.hits * 100 / gets_served)
#
#         graphing_data = (MemcacheData.query.order_by(MemcacheData.timestamp.desc()).limit(120))[::-1]
#         graph_labels = [str(row.timestamp) for row in graphing_data]
#         num_items_val = [row.num_items for row in graphing_data]
#         current_size_val = [row.current_size for row in graphing_data]
#         gets_served_val = [(row.hits + row.misses) for row in graphing_data]
#         posts_served_val = [row.posts_served for row in graphing_data]
#         miss_rate_val = [(0 if (row.hits + row.misses == 0) else (row.misses * 100 / (row.hits + row.misses))) for row
#                          in graphing_data]
#         hit_rate_val = [(0 if (row.hits + row.misses == 0) else (row.hits * 100 / (row.hits + row.misses))) for row in
#                         graphing_data]
#
#     if frontend_data['update_active_nodes']:
#         frontend_data['update_active_nodes'] = False
#         flash(f'SIZE OF CACHE POOL HAS CHANGED: from {frontend_data["old_active_nodes"]} to {frontend_data["new_active_nodes"]}')
#     return render_template('memcache_stats.html', title="ECE1779 - Group 25 - View memcache Statistics",
#                            max_size=max_size, num_items=num_items, current_size=current_size, gets_served=gets_served,
#                            posts_served=posts_served, miss_rate=miss_rate, hit_rate=hit_rate,
#                            current_policy=current_policy, labels=graph_labels, hit_rate_val=hit_rate_val,
#                            miss_rate_val=miss_rate_val, posts_served_val=posts_served_val,
#                            gets_served_val=gets_served_val,
#                            num_items_val=num_items_val, current_size_val=current_size_val)


# adding a Logging start Button
@frontend.route('/start_update', methods=['GET', 'POST'])
def start_update():
    if frontend_data["commits_running"]:
        flash("Update Thread Already Running!")
    else:
        # Tell memapp to start logging data every 5 seconds
        logging.info("Asking memcache to start logging data...")
        response = requests.post(Config.MANAGER_APP_URL + "start_logging")
        if response.status_code == 200:
            logging.info("Memapp successfully logging to database!")
            flash("Update Thread Started!")
            frontend_data["commits_running"] = True
        else:
            logging.info("FAIL!!! Memapp could not start logging to the database...")
            flash("Update Thread Failed to Start, Please try again")

    return redirect('/')


@frontend.route('/update_num_active_nodes', methods=['GET', 'POST'])
def update_num_active_nodes():
    frontend_data['old_active_nodes'] = int(request.form["old_active_nodes"])
    frontend_data['new_active_nodes'] = int(request.form["new_active_nodes"])
    frontend_data['update_active_nodes'] = True
    return jsonify({"status": "success", "status_code": 200})




#####################################
#                                   #
#        API INTERFACE BEGIN        #
#                                   #
#####################################

@frontend.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    logging.info("API call to DELETE_ALL")
    # First delete from database
    try:
        with frontend.app_context():
            images = Image.query.order_by(Image.timestamp.asc())
            for image in images:
                db.session.delete(image)
            db.session.commit()
            db_success = True
            logging.info("Successfully deleted all entries from database")
    except Exception:
        logging.info("FAIL!!! Could not delete from database")
        db_success = False

    # Next delete from memcache
    response = requests.post(Config.MANAGER_APP_URL + 'clearcache')
    if response.status_code == 200:
        logging.info("Successfully deleted all entries from cache")
        cache_success = True
    else:
        logging.info("FAIL!!! Could not delete from memcache")
        cache_success = False

    # Next delete from S3
    response = requests.post(Config.S3_APP_URL + "delete_all")
    jsonResponse = response.json()
    if jsonResponse['status_code'] == 200:
        logging.info("Successfully deleted all entries from database, cache, and disk")
        s3_success = True
    else:
        logging.info("FAIL!!! Could not delete key/image pairs from S3")
        s3_success = False

    # Verify that everything passed
    if db_success and cache_success and s3_success:
        logging.info("Successfully deleted all entries from database, cache, and disk")
        return jsonify({"success": "true"})
    else:
        logging.info("FAIL!!! Could not complete delete request. See above logs for causes.")
        return jsonify({"success": "false"})


@frontend.route('/api/list_keys', methods=['POST'])
def api_list_keys():
    logging.info("API call to LIST_KEYS")
    try:
        keys = []
        with frontend.app_context():
            images = Image.query.order_by(Image.timestamp.asc())
            for image in images:
                keys.append(image.id)
        logging.info("Successfully retrieved keys from database")
    except Exception:
        logging.info("FAIL!!! Could not get list of keys from database. Returning empty list.")
        keys = []
    return jsonify({"success": "true", "keys": keys})


@frontend.route('/api/upload', methods=['GET', 'POST'])
def api_upload():
    logging.info("API call to UPLOAD")
    memapp_success = False
    request_key = request.form["key"]
    request_file = request.files["file"]
    try:
        logging.info(f"Attempting to upload file {request_file.filename} with key {request_key}")

        # Check if the file type is valid
        if request_file.filename.split(".")[-1].strip() not in Config.ALLOWED_EXTENSIONS:
            logging.info("File type is not allowed - please upload a PNG, JPEG, JPG, or GIF file.")
            return {"success": "false", "key": request_key}

        # Upload to database
        with frontend.app_context():
            image = Image.query.filter_by(id=request_key).first()
            if image:
                db.session.delete(image)
                db.session.commit()
            image = Image(id=request_key, value=Config.S3_BUCKET_NAME)
            db.session.add(image)
            db.session.commit()
            logging.info(f"Image successfully saved in database")
            db_success = True
    except Exception:
        db_success = False

    if db_success:
        try:
            logging.info(f"Invalidating key = {request_key} in memcache")
            requests.post(Config.MANAGER_APP_URL + "/invalidate_key", data={'key': request_key})
            logging.info(f"Attempting to convert file to string to save in memcache")
            b64string = b64encode(request_file.read()).decode("ASCII")
            logging.info(f"Image successfully converted to string")
            response = requests.post(Config.MANAGER_APP_URL + "put", data={"key": request_key, "value": b64string})
            jsonResponse = response.json()
            if jsonResponse["status_code"] == 200:
                logging.info("Image successfully saved in cache")
                memapp_success = True
            elif jsonResponse["status_code"] == 201:
                logging.info("Image was too big for the cache, continuing...")
                memapp_success = True
            else:
                logging.info("FAIL!!! Image could not be saved in cache!")
                memapp_success = False

            # Store on S3
            response = requests.post(Config.S3_APP_URL + "upload_image",
                                     data={'key': request_key, 'value': b64string, 'bucket': Config.S3_BUCKET_NAME})
            jsonResponse = response.json()
            if jsonResponse['status_code'] == 200:
                logging.info("Successfully saved image to S3!")
                s3_success = True
            else:
                logging.info("FAIL!!! Could not save image to S3")
                s3_success = False

        except Exception:
            logging.info(f"FAIL!!! Failed to convert image to string or bad response from memapp")
            memapp_success = False

    if db_success and memapp_success and s3_success:
        logging.info("Successfully uploaded the image to disk, database, and cache")
        return {"success": "true", "key": request_key}
    else:
        logging.info("FAIL!!! Could not upload the image. See previous logs for cause.")
        return {"key": request_key, "success": "false"}


@frontend.route('/api/key/<string:key>', methods=['GET', 'POST'])
def api_retrieval(key):
    logging.info("API call to KEY/<key>")
    # First look in cache:
    response = requests.post(Config.MANAGER_APP_URL + "get", data={"key": key})
    jsonResponse = response.json()
    if jsonResponse["status_code"] == 200:
        logging.info(f"Image successfully found in cache")
        encoded_image = response.json()["value"]
        logging.info(f"Image has length: {len(encoded_image)}")
        in_cache = True
        success = 'true'
    else:
        logging.info("Could not find image in cache. Retrieving from S3")
        in_cache = False
    # Then check on disk:
    if not in_cache:
        image = Image.query.filter_by(id=key).first()
        if image is None:
            logging.info("No image with this key in database. Invalid key!")
            return jsonify({"success": "false", "key": key, "content": None})
        logging.info("Successfully found image in database")
        bucket = image.value

        response = requests.post(Config.S3_APP_URL + "download_image",
                                 data={'key': key, 'bucket': bucket})
        jsonResponse = response.json()
        if jsonResponse['status_code'] != 200:
            logging.info("FAIL!!! Could not return the image to cache - S3 failure")
            return jsonify({"success": "false", "key": key, "content": None})
        encoded_image = jsonResponse['value']
        logging.info("Attempting to encode image to send as json...")
        success = 'true'

        # Store in cache
        logging.info(f"Successfully retrieved b64string from s3_app for key = {key}")
        response = requests.post(Config.MANAGER_APP_URL + "/put", data={'key': key, 'value': encoded_image})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info("Successfully uploaded image to cache")
        else:
            logging.info("FAIL!!! Could not store image back into cache!")
            flash("WARNING! Image is too big for the cache...")

    logging.info("Successfully retrieved image")

    return jsonify({"success": success, "key": key, "content": encoded_image})


@frontend.route('/api/getRate', methods=['GET', 'POST'])
def api_get_rate():
    args = request.args.to_dict()
    hits, misses = aws_helper.get_hits_and_misses_from_cloudwatch()
    if hits + misses == 0:
        miss_rate = 0.0
        hit_rate = 0.0
    else:
        miss_rate = float(misses / (hits + misses))
        hit_rate = 1 - miss_rate
    if args["rate"] == "hit":
        return jsonify({"success": "true", "rate": args["rate"], "value": hit_rate})
    elif args["rate"] == "miss":
        return jsonify({"success": "true", "rate": args["rate"], "value": miss_rate})
    else:
        return jsonify({"success": "failure", "rate": args["rate"], "value": None})


@frontend.route('/api/configure_cache', methods=['GET', 'POST'])
def api_configure_cache():
    logging.info("API call to configure_cache...")
    # These go to autoscaler
    args = request.args.to_dict()
    if 'mode' in args:
        if args["mode"] == "auto":
            mode = "1"
        else:
            mode = "0"
    else:
        mode = "None"
    if 'numNodes' in args:
        numNodes = args["numNodes"]
    else:
        numNodes = "None"
    if "expRatio" in args:
        expand_multiplier = args["expRatio"]
    else:
        expand_multiplier = "None"
    if "shrinkRatio" in args:
        shrink_multiplier = args["shrinkRatio"]
    else:
        shrink_multiplier = "None"
    if "maxMiss" in args:
        expand_threshold = args["maxMiss"]
    else:
        expand_threshold = "None"
    if "minMiss" in args:
        shrink_threshold = args["minMiss"]
    else:
        shrink_threshold = "None"

    autoscaler_data = {
        'mode': mode,
        'numNodes': numNodes,
        'expand_threshold': expand_threshold,
        'shrink_threshold': shrink_threshold,
        'expand_multiplier': expand_multiplier,
        'shrink_multiplier': shrink_multiplier
    }
    response = requests.post(Config.AUTOSCALER_APP_URL + "configure_autoscaler", data=autoscaler_data)
    jsonResponse = response.json()
    if jsonResponse["status_code"] == 200:
        autoscaler_success = True
        logging.info("Successfully pushed configuration data to autoscaler!")
    else:
        autoscaler_success = False
        logging.info("ERROR! Failed to push configuration data to autoscaler...")

    if 'cacheSize' in args:
        cache_size = args["cacheSize"]
    else:
        cache_size = "None"
    if 'policy' in args:
        policy = args["policy"]
    else:
        policy = "None"

    response = requests.post(Config.MANAGER_APP_URL + "configure_autoscaler", data={"cachesize": cache_size, "policy": policy})
    jsonResponse = response.json()
    if jsonResponse["status_code"] == 200:
        manager_success = True
        logging.info("Successfully pushed configuration data to manager app!")
    else:
        manager_success = False
        logging.info("ERROR! FAiled to push configuration data to manager app...")

    if manager_success and autoscaler_success:
        return jsonify({"success": "true", "mode": args["mode"], "numNodes": int(args["numNodes"]), "cacheSize": int(args["cacheSize"]), "policy": args["policy"]})
    else:
        return jsonify({"success": "failure", "mode": args["mode"], "numNodes": int(args["numNodes"]),
                        "cacheSize": int(args["cacheSize"]), "policy": args["policy"]})


@frontend.route('/api/getNumNodes', methods=['GET', 'POST'])
def get_num_nodes():
    logging.info("API call to getNumNodes...")
    response = requests.post(Config.AUTOSCALER_APP_URL + "getNumNodes")
    jsonResponse = response.json()
    if jsonResponse["status_code"] == 200:
        numNodes = jsonResponse["numNodes"]
        success = "true"
    else:
        numNodes = None
        success = "false"
    return jsonify({"success": success, "numNodes": numNodes})
