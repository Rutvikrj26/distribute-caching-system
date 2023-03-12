import io
import logging
import aws_helper
from base64 import b64encode, b64decode
from werkzeug.datastructures import FileStorage
from s3_app import s3_app
from flask import request, jsonify

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@s3_app.route("/", methods=['GET'])
def index():
    return jsonify({"status": "success", "status_code": 200})


@s3_app.route('/download_image', methods=['GET', 'POST'])
def download_image():
    logging.info("Getting image from S3...")
    key = request.form["key"]
    bucket = request.form["bucket"]
    logging.info(f"Key = {key} and bucket = {bucket}")
    my_file_storage = aws_helper.download_fileobj(key, bucket)
    logging.info(f"Received my_file_storage...")
    if my_file_storage is None:
        logging.info("Error! Could not get image from S3...")
        return jsonify({"status": "failure", "value": None, "status_code": 400})
    b64string = b64encode(my_file_storage.read()).decode("ASCII")
    logging.info("Successfully returning image from S3!")
    return jsonify({"status": "success", "value": b64string, "status_code": 200})


@s3_app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    logging.info("Uploading image to S3...")
    key = request.form["key"]
    bucket = request.form["bucket"]
    b64string = request.form["value"]
    logging.info(f"Key = {key} and bucket = {bucket} and length of b64string = {len(b64string)}")
    my_file_storage = FileStorage(io.BytesIO(b64decode(b64string.encode("ASCII"))))
    logging.info(f"File storage object created without error")
    upload_success = aws_helper.upload_fileobj(key, my_file_storage, bucket)
    logging.info(f"upload_success boolean = {upload_success}")
    if not upload_success:
        logging.info("ERROR! Failed to upload to S3...")
        return jsonify({"status": "failure", "status_code": 400})
    logging.info("Successfully uploaded image to S3!")
    return jsonify({"status": "success", "status_code": 200})


@s3_app.route('/delete_all', methods=['GET', 'POST'])
def delete_all_from_s3():
    delete_success = aws_helper.delete_all_from_s3()
    if not delete_success:
        logging.info("ERROR! Could not delete all images from S3...")
        return jsonify({"status": "failure", "status_code": 400})
    logging.info("Successfully deleted all images from S3!")
    return jsonify({"status": "success", "status_code": 200})
