import io
import time
import logging
import requests
import aws_helper
from werkzeug.datastructures import FileStorage

from config import Config
from base64 import b64encode, b64decode
from flask import render_template, request, flash, jsonify
from frontend.forms import SubmitButton, UploadForm, DisplayForm, MemcacheConfigForm, RegistrationForm, LoginForm
from frontend import frontend, db, bcrypt
import boto3
from flask import flash, redirect, url_for
from flask_login import UserMixin, login_required, logout_user, current_user, login_user
from frontend import login_manager

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

global commits_running
commits_running = False

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('users')  # Replace 'users' with the name of your table

class User(UserMixin):
    def __init__(self, email, password, status):
        self.email = email
        self.password = password
        self.status = status

    def get_id(self):
        return self.email

@login_manager.user_loader
def load_user(email_status):
    email, status = email_status.split('_')
    user = aws_helper.dynamo_get_user(email_status)
    if not user:
        return None
    return User(email=email, password=user['password'], status=int(status))

# Extra Decorator to identify if the user logged in is employee or not
from functools import wraps
from flask_login import current_user
from flask import flash, redirect, url_for

def employee_login_required(f):
    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        status = int(current_user.get_id().split('_')[-1])
        if current_user.is_authenticated and status == 0:
            return f(*args, **kwargs)
        else:
            flash('You do not have access to this page.', 'danger')
            return redirect(url_for('index'))
    return decorated_function

def customer_login_required(f):
    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        status = int(current_user.get_id().split('_')[-1])
        if current_user.is_authenticated and status == 1:
            return f(*args, **kwargs)
        else:
            flash('You do not have access to this page.', 'danger')
            return redirect(url_for('index'))
    return decorated_function

def admin_login_required(f):
    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        status = int(current_user.get_id().split('_')[-1])
        if current_user.is_authenticated and status == 2:
            return f(*args, **kwargs)
        else:
            flash('You do not have access to this page.', 'danger')
            return redirect(url_for('index'))
    return decorated_function

@frontend.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        # updating the user table using the AWS Helper Function
        email = form.email.data
        password = hashed_password
        status = form.status.data
        email_status = email + '_' + str(status)
        response_code = aws_helper.dynamo_add_user(email_status, password=hashed_password)
        if response_code == 200:
            flash('Your account has been created! You are now able to log in', 'success')
            logging.info(f"New user registered: {form.email.data}") # Log the new user's email
            return redirect(url_for('login'))
        elif response_code == 400:
            flash('Registration failed. Please try again.')
            logging.info(f"Registration failed: {form.email.data}") # Log the new user's email
        else:
            flash('Something went wrong on our side, please try again after some time.')
            logging.info(f"AWS Response Code : {response_code}") # Log the new user's email

    return render_template('register.html', title='Register', form=form)

@frontend.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        status = form.status.data
        email_status = email + '_' + str(status)
        user = aws_helper.dynamo_get_user(email_status)  # This retrieves the user from DynamoDB by email
        if user is not []:
            if bcrypt.check_password_hash(user[0]['password'], password):
                email, status = email_status.split('_')
                user_obj = User(email, user[0]['password'], status)
                login_manager.login_user(user_obj)  # Use the login_user from flask_login to support DynamoDB
                flash('You have been logged in!', 'success')
                logging.info(f"User logged in: {email}")  # Log the user's email when they log in
                return redirect(url_for('index'))
            else:
                flash('No such email / password combination exists.', 'danger')
                logging.info(f"Login failed: {email}") # Log the user's email when they log in
        else:
            flash('There was some error in logging you in. Please try again later.', 'danger')
            logging.info(f"Login failed: {email}") # Log the user's email when they log in
    return render_template('login.html', title='Log In', form=form)

@frontend.route('/logout')
@login_required
def logout():
    logout_user()
    logging.info("User logged out") # Log when a user logs out
    flash('You have been logged out.')
    return redirect(url_for('index'))



@frontend.route('/')
@frontend.route('/index')
def index():
    return render_template('index.html', title="ECE1779 - Group 25 - Gauri Billore, Joseph Longpre, Rutvik Solanki")


# 1. Upload to disk WORKS
# 2. Upload to database WORKS
# 3. Upload to memapp WORKS
# 4. Logging statement WORKS
@frontend.route('/upload', methods=['GET', 'POST'])
@employee_login_required
def upload():
    logging.info("Accessed UPLOAD page")
    form = UploadForm()
    if form.validate_on_submit():
        email = form.customer.data
        email_prefix = email.split("@")[0].strip()
        key = email_prefix + "-" + form.key.data
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
        status_code = aws_helper.dynamo_add_image(key, Config.S3_BUCKET_NAME)
        if status_code == 200:
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

# TODO: Only upload route above has been switched over to S3 and DynamoDB - the rest is still to-do...

# 1. Retrieval from disk WORKS
# 2. Retrieval form memapp WORKS
# 3. Display in HTML WORKS
# 4. Logging statement WORKS
@frontend.route('/display', methods=['GET', 'POST'])
@customer_login_required
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
            image_info = aws_helper.dynamo_get_images(Config.S3_BUCKET_NAME)
            if image_info is None or image_info == []:
                logging.info("FAIL!!! No images associated with this bucket...")
                flash("Could not find an image associated with this key.")
                return redirect(url_for('display'))
            images = []
            for image in image_info:
                image_bucket = image['Bucket']
                image_key = image['Key']
                my_file_storage = aws_helper.download_fileobj(image_key, image_bucket)
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
                key = image_info[i]['Key']
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
@admin_login_required
def show_delete_keys():
    logging.info("Accessed DELETE KEYS page")
    form = SubmitButton()
    images = aws_helper.dynamo_get_images(Config.S3_BUCKET_NAME)
    keys = []
    for image in images:
        keys.append(image["Key"])
    if form.validate_on_submit():
        # First delete from database:
        logging.info("Deleting images table from DynamoDB...")
        delete_success = aws_helper.dynamo_delete_images_table()
        if delete_success:
            logging.info("Table successfully deleted! Recreating...")
            time.sleep(10)
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
                           form=form, keys=keys)


# 1. Call to database WORKS
# 2. Check for empty database WORKS
# 3. Logging statement WORKS
@frontend.route('/memcache_config', methods=['GET', 'POST'])
@admin_login_required
def memcache_config():
    logging.info("Accessed MEMCACHE CONFIGURATION page")
    response = requests.post(Config.MEMAPP_URL + 'get_all_keys')
    jsonResponse = response.json()
    keys = jsonResponse["keys"]
    keys = None if len(keys) == 0 else keys

    response = requests.get(Config.MEMAPP_URL + "get_cache_capacity")
    jsonResponse = response.json()
    maxSize = int(jsonResponse["cacheSize"])

    form = MemcacheConfigForm(capacity=maxSize)
    if form.validate_on_submit():
        response = requests.post(Config.MEMAPP_URL+"/reconfig",  params={'cacheSize': form.capacity.data})
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
# GB: We can call it "developer dashboard" and can use it to monitor the number of requests etc.
#     Also can use it to show that our cache size grows/shrinks based on miss rate.
@frontend.route('/memcache_stats', methods=['GET'])
@admin_login_required
def memcache_stats():
    logging.info("Accessed MEMCACHE STATISTICS page")
    num_nodes_stats = aws_helper.get_data_from_cloudwatch(Config.num_active_nodes, 30)
    logging.info("Got last 30 min. stats from CloudWatch")
    num_nodes_labels, num_nodes = ([] for i in range(2))
    for row in num_nodes_stats:
        num_nodes_labels.append(str(row[0]))
        num_nodes.append(row[1])

    # # Retrieve the metrics data for the last 30 minutes at 1-minute granularity
    graphing_data = aws_helper.get_memcache_stats()
    graph_labels, num_items_val, current_size_val, gets_served_val, posts_served_val = ([] for i in range(5))
    for row in graphing_data:
        graph_labels.append(str(row[0]))
        gets_served_val.append(row[1] + row[2])
        posts_served_val.append(row[3])
        num_items_val.append(row[4])
        current_size_val.append(row[5])

    num_items_agg = [num_items_val[0]]
    current_size_agg = [current_size_val[0]]
    for i in range(1, (len(graphing_data))):
        num_items_sum = num_items_agg[i - 1] + num_items_val[i]
        num_items_agg.append(num_items_sum)
        current_size_sum = current_size_agg[i - 1] + current_size_val[i]
        current_size_agg.append(current_size_sum)

    miss_rate_val = [(0 if (row[1] + row[2] == 0) else (row[2] * 100 / (row[1] + row[2]))) for row in graphing_data]
    hit_rate_val = [(0 if (row[1] + row[2] == 0) else (row[1] * 100 / (row[1] + row[2]))) for row in graphing_data]

    return render_template('memcache_stats.html', title="ECE1779 - Group 25 - View memcache Statistics",
                               labels=graph_labels, hit_rate_val=hit_rate_val,
                               miss_rate_val=miss_rate_val, posts_served_val=posts_served_val, gets_served_val=gets_served_val,
                               num_items_val=num_items_agg, current_size_val=current_size_agg)


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
