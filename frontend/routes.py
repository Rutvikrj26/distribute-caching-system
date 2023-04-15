import io
import os
import logging
import requests
import aws_helper
from werkzeug.datastructures import FileStorage

from config import Config
from base64 import b64encode, b64decode
from frontend.models import Image, MemcacheConfig
from frontend import frontend
from memapp import memapp
from memapp.models import MemcacheData
from flask import render_template, redirect, url_for, request, flash, jsonify
from frontend.forms import SubmitButton, UploadForm, DisplayForm, MemcacheConfigForm

logger = logging.getLogger()
logger.setLevel(logging.INFO)

global commits_running
commits_running = False

@frontend.route('/')
@frontend.route('/index')
def index():
    return render_template('index.html', title="ECE1779 - Group 25 - Gauri Billore, Joseph Longpre, Rutvik Solanki")


# 1. Upload to disk WORKS
# 2. Upload to database WORKS
# 3. Upload to memapp WORKS
# 4. Logging statement WORKS
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

        # Invalidate key in cache
        requests.post(Config.MEMAPP_URL + "/invalidate_key", data={'key': key})

        # Store on S3
        logging.info("Uploading image to S3...")
        b64string = b64encode(file.read()).decode("ASCII")
        my_file_storage = FileStorage(io.BytesIO(b64decode(b64string.encode("ASCII"))))
        upload_success = aws_helper.upload_fileobj(key, my_file_storage, Config.S3_BUCKET_NAME)
        if not upload_success:
            logging.info("ERROR! Failed to upload to S3...")
        else:
            logging.info("Successfully uploaded image to S3!")

        # Store in database
        logging.info("Attempting to save key/bucket data to dynamodb...")
        success = aws_helper.dynamo_add_image(key, Config.S3_BUCKET_NAME)
        if success:
            logging.info("Successfully saved image details to database")
        else:
            logging.info("FAIL!!! Could not save image details to database")
            flash("ERROR: Could not upload the image to the database.")
            return redirect(url_for('upload'))

        # Store in cache
        try:
            response = requests.post(Config.MEMAPP_URL+"/put", data={'key': key, 'value': b64string})
            jsonResponse = response.json()
            if jsonResponse["status_code"] == 200:
                logging.info("Successfully uploaded image to cache")
            else:
                logging.info("FAIL!!! Received non-200 response from memapp")
                flash("ERROR: Bad response from cache.")
                return redirect(url_for('upload'))
        except Exception:
            logging.info("FAIL!!! Error opening file, encoding file, or sending encoded file to cache. See above for cause.")
            flash("ERROR: Could not store image in cache.")
            return redirect(url_for('upload'))
        flash("Image successfully uploaded!")
        return redirect(url_for('upload'))

    return render_template('upload.html', title="ECE1779 - Group 25 - Upload a Key-Value Pair", form=form)


# 1. Retrieval from disk WORKS
# 2. Retrieval form memapp WORKS
# 3. Display in HTML WORKS
# 4. Logging statement WORKS
@frontend.route('/display', methods=['GET', 'POST'])
def display():
    logging.info("Accessed DISPLAY page")
    form = DisplayForm()
    if form.validate_on_submit():
        # Try cache first
        key = form.key.data
        response = requests.post(Config.MEMAPP_URL+"/get", data={'key': key})
        jsonResponse = response.json()
        if jsonResponse["status_code"] == 200:
            logging.info("Image found in cache, accessing...")
            b64string = jsonResponse['value']
            logging.info("Image retrieved from cache...")
            image_location = 'data:image/png;base64,' + b64string
        # Else, go to S3
        else:
            logging.info("Image NOT in cache, going to disk...")
            image_keys = aws_helper.dynamo_get_images(Config.S3_BUCKET_NAME)
            if image_keys is None or image_keys == []:
                logging.info("FAIL!!! No images associated with this bucket...")
                flash("Could not find an image associated with this key.")
                return redirect(url_for('display'))
            images = []
            for image_key in image_keys:
                my_file_storage = aws_helper.download_fileobj(image_key, Config.S3_BUCKET_NAME)
                images.append(my_file_storage)
            if len(images) == 0:
                logging.info("FAIL!!! Image not in cache or on disk - BAD KEY")
                flash("Could not find an image associated with this key.")
                return redirect(url_for('display'))
            else:
                # TODO: We can show multiple images when we need to, but choosing just one to start
                my_file_storage = images[0]
                b64string = b64encode(my_file_storage.read()).decode("ASCII")
                image_location = 'data:image/png;base64,' + b64string
            # Now need to store back in the cache!
            for i in range(0, len(images)):
                key = image_keys[i]
                image = images[i]
                logging.info(f"PUTting image with key = {key} into cache")
                b64string = b64encode(image.read()).decode("ASCII")
                response = requests.post(Config.MEMAPP_URL+"/put", data={'key': key, 'value': b64string})
                jsonResponse = response.json()
                if jsonResponse["status_code"] == 200:
                    logging.info("Successfully uploaded image to cache")
                else:
                    logging.info("FAIL!!! Could not store image back into cache!")
                    flash("WARNING! Image is too big for the cache...")
        flash(f"Showing image for key = {key}")
        return render_template('display.html', title="ECE1779 - Group 25 - Display an Image", form=form,
                               image_location=image_location)
    return render_template('display.html', title="ECE1779 - Group 25 - Display an Image",
                           form=form, image_location=None)


# 1. Delete from database WORKS
# 2. Delete from disk WORKS
# 3. Delete from memapp WORKS
# 4. Logging statement WORKS
@frontend.route('/show_delete_keys', methods=['GET', 'POST'])
def show_delete_keys():
    logging.info("Accessed DELETE KEYS page")
    form = SubmitButton()
    images = Image.query.order_by(Image.timestamp.asc())
    if form.validate_on_submit():
        # First delete from database:
        logging.info("Deleting images table from DynamoDB...")
        delete_success = aws_helper.dynamo_delete_images_table()
        if delete_success:
            logging.info("Table successfully deleted! Recreating...")
            create_success = aws_helper.dynamo_create_image_table()
            if create_success:
                logging.info("Table successfully recreated!")
            else:
                logging.info("FAIL!!! Could not recreate the table...")
                flash("WARNING: Could not recreate the DynamoDB images table...")
        else:
            logging.info("FAIL!!! Could not delete the DynamoDB images table...")
            flash("WARNING: Could not delete the DynamoDB images table...")

        # Next, delete from disk:
        # TODO: Need to get all buckets from users table first and iterate
        s3_delete_success = aws_helper.delete_all_from_s3(Config.S3_BUCKET_NAME)
        if s3_delete_success:
            logging.info(f"Successfully deleted all images from S3 with bucket = {Config.S3_BUCKET_NAME}")
        else:
            logging.info("FAIL!!! Could not delete key/image pairs from S3")
            flash("WARNING: Could not delete key/image pairs from S3...")

        # Last, delete from cache
        try:
            response = requests.post(Config.MEMAPP_URL + 'clearcache')
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
    return render_template('show_delete_keys.html', title="ECE1779 - Group 25 - Show and Delete All Keys",
                           form=form, images=images)


# 1. Call to database WORKS
# 2. Check for empty database WORKS
# 3. Logging statement WORKS
@frontend.route('/memcache_config', methods=['GET', 'POST'])
def memcache_config():
    logging.info("Accessed MEMCACHE CONFIGURATION page")
    response = requests.post(Config.MEMAPP_URL + 'get_all_keys')
    jsonResponse = response.json()
    keys = jsonResponse["keys"]
    keys = None if len(keys) == 0 else keys
    # TODO: Need to get this data directly from memcache with a request
    maxSize = 2
    form = MemcacheConfigForm(capacity=maxSize)
    if form.validate_on_submit():
        # TODO: Need to send an update directly to memcache
        response = requests.post(Config.MEMAPP_URL+"/refresh_config")
        if response.status_code == 200:
            logging.info(f"Memcache configuration updated with maxSize = {form.capacity.data}")
            flash("Successfully updated the memcache configuration!")
        if form.clear_cache.data:
            response = requests.post(Config.MEMAPP_URL + 'clearcache')
            if response.status_code == 200:
                logging.info("Successfully deleted all entries from cache")
                flash("Successfully deleted all key/value pairs from cache!")
            else:
                logging.info("FAIL!!! Could not delete from memcache")
                flash("ERROR: Could not delete all key/value pairs from cache")
        return redirect(url_for('memcache_config'))
    return render_template('memcache_config.html', title="ECE1779 - Group 25 - Configure the memcache", form=form, keys=keys)


# TODO: Do we still want this page? Does it have any use?
@frontend.route('/memcache_stats', methods=['GET'])
def memcache_stats():
    logging.info("Accessed MEMCACHE STATISTICS page")

    # First get current memcache configuration
    current_memcache_config = MemcacheConfig.query.filter_by(id=1).first()
    current_policy = "Random Replacement" if current_memcache_config.isRandom == 1 else "Least Recently Used"
    max_size = current_memcache_config.maxSize

    # Next get memcache statistics, populated by memcache
    with memapp.app_context():
        memcache_data = MemcacheData.query.order_by(MemcacheData.timestamp.desc()).first()
        num_items = memcache_data.num_items
        current_size = memcache_data.current_size
        posts_served = memcache_data.posts_served
        gets_served = memcache_data.misses + memcache_data.hits
        miss_rate = 0 if (gets_served == 0) else (memcache_data.misses * 100 / gets_served)
        hit_rate = 0 if (gets_served == 0) else (memcache_data.hits * 100 / gets_served)


        graphing_data = (MemcacheData.query.order_by(MemcacheData.timestamp.desc()).limit(120))[::-1]
        graph_labels = [str(row.timestamp) for row in graphing_data]
        num_items_val = [row.num_items for row in graphing_data]
        current_size_val = [row.current_size for row in graphing_data]
        gets_served_val = [(row.hits + row.misses) for row in graphing_data]
        posts_served_val = [row.posts_served for row in graphing_data]
        miss_rate_val = [( 0 if (row.hits + row.misses == 0) else (row.misses * 100 / (row.hits + row.misses))) for row in graphing_data]
        hit_rate_val = [( 0 if (row.hits + row.misses == 0) else (row.hits * 100 / (row.hits + row.misses))) for row in graphing_data]


    return render_template('memcache_stats.html', title="ECE1779 - Group 25 - View memcache Statistics",
                           max_size=max_size, num_items=num_items, current_size=current_size, gets_served=gets_served,
                           posts_served=posts_served, miss_rate=miss_rate, hit_rate=hit_rate,
                           current_policy=current_policy, labels=graph_labels, hit_rate_val=hit_rate_val,
                           miss_rate_val=miss_rate_val, posts_served_val=posts_served_val, gets_served_val=gets_served_val,
                           num_items_val=num_items_val, current_size_val=current_size_val)


# Endpoint Tested : OK
@frontend.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    logging.info("API call to DELETE_ALL")
    # First delete from database
    logging.info("Deleting images table from DynamoDB...")
    db_success = aws_helper.dynamo_delete_images_table()
    if db_success:
        logging.info("Table successfully deleted! Recreating...")
        create_success = aws_helper.dynamo_create_image_table()
        if create_success:
            logging.info("Table successfully recreated!")
        else:
            logging.info("FAIL!!! Could not recreate the table...")
    else:
        create_success = False
        logging.info("FAIL!!! Could not delete the DynamoDB images table...")

    # Next delete from memcache
    response = requests.post(Config.MEMAPP_URL + 'clearcache')
    if response.status_code == 200:
        logging.info("Successfully deleted all entries from cache")
    else:
        logging.info("FAIL!!! Could not delete from memcache")

    # Also clear files from S3
    # TODO: Need to iterate through all buckets
    s3_delete_success = aws_helper.delete_all_from_s3(Config.S3_BUCKET_NAME)
    if s3_delete_success:
        logging.info(f"Successfully deleted all images from S3 with bucket = {Config.S3_BUCKET_NAME}")
    else:
        logging.info("FAIL!!! Could not delete key/image pairs from S3")

    # Verify that everything passed
    if db_success and create_success and response.status_code == 200 and s3_delete_success:
        logging.info("Successfully deleted all entries from database, cache, and disk")
        return jsonify({"success": "true"})
    else:
        logging.info("FAIL!!! Could not complete delete request. See above logs for causes.")
        return jsonify({"success": "false"})


# Endpoint Tested : OK
@frontend.route('/api/list_keys', methods=['POST'])
def api_list_keys():
    logging.info("API call to LIST_KEYS")
    # TODO: Again, need to iterate over buckets
    keys = aws_helper.dynamo_get_images(Config.S3_BUCKET_NAME)
    return jsonify({"success": "true", "keys": keys})


# Endpoint Tested : OK
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
        success = aws_helper.dynamo_add_image(request_key, Config.S3_BUCKET_NAME)
        if success:
            logging.info(f"Image successfully saved in database")
            db_success = True
        else:
            logging.info(f"Failed to save in database...")
            db_success = False
    except Exception:
        db_success = False

    if db_success:
        try:
            logging.info(f"Invalidating key = {request_key} in memcache")
            requests.post(Config.MEMAPP_URL + "/invalidate_key", data={'key': request_key})
            logging.info(f"Attempting to convert file to string to save in memcache")
            b64string = b64encode(request_file.read()).decode("ASCII")
            logging.info(f"Image successfully converted to string")
            response = requests.post(Config.MEMAPP_URL+"put", data={"key": request_key, "value": b64string})
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
            my_file_storage = FileStorage(io.BytesIO(b64decode(b64string.encode("ASCII"))))
            s3_success = aws_helper.upload_fileobj(request_key, my_file_storage, Config.S3_BUCKET_NAME)
            if not s3_success:
                logging.info("ERROR! Failed to upload to S3...")
            else:
                logging.info("Successfully uploaded image to S3!")

        except Exception:
            logging.info(f"FAIL!!! Failed to convert image to string or bad response from memapp")
            memapp_success = False

    if db_success and memapp_success:
        logging.info("Successfully uploaded the image to disk, database, and cache")
        return {"success": "true", "key": [request_key]}
    else:
        logging.info("FAIL!!! Could not upload the image. See previous logs for cause.")
        return {"success": "false", "key": [request_key]}


# Endpoint Tested : OK
@frontend.route('/api/key/<string:key>', methods=['GET', 'POST'])
def api_retrieval(key):
    logging.info("API call to KEY/<key>")
    # First look in cache:
    response = requests.post(Config.MEMAPP_URL + "get", data={"key": key})
    jsonResponse = response.json()
    if jsonResponse["status_code"] == 200:
        logging.info(f"Image successfully found in cache")
        encoded_image = response.json()["value"]
        logging.info(f"Image has length: {len(encoded_image)}")
        in_cache = True
        success = 'true'
    else:
        logging.info("Could not find image in cache. Retrieving from disk")
        in_cache = False
        success = 'false'
        encoded_image = None
    # Then check on disk:
    if not in_cache:
        # TODO: Need to get bucket for user, but assume 1 bucket for now
        image = aws_helper.download_fileobj(key, Config.S3_BUCKET_NAME)
        if image is not None:
            logging.info("Successfully found image on S3!")
            success = 'true'
        else:
            logging.info("FAIL!!! Could not find image on S3...")
            success = 'false'
        logging.info("Attempting to encode image to send as json...")
        encoded_image = b64encode(image.read()).decode("ASCII")
        logging.info("Successfully encoded image")

    logging.info("Successfully retrieved image")
    return jsonify({"success": success, "key": [key], "content": encoded_image})

# TODO: Will we need this?
# adding a Logging start Button 
@frontend.route('/start_update', methods=['GET', 'POST'])
def start_update():
    if commits_running:
        flash("Update Thread Already Running!")
    else:
        # Tell memapp to start logging data every 5 seconds
        logging.info("Asking memcache to start logging data...")
        response = requests.post(Config.MEMAPP_URL + "update_db")
        if response.status_code == 200:
            logging.info("Memapp successfully logging to database!")
            flash("Update Thread Started!")
        else:
            logging.info("FAIL!!! Memapp could not start logging to the database...")        
            flash("Update Thread Failed to Start, Please try again")

    return redirect('/')
