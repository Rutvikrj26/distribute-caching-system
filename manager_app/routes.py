import helper
import logging
from manager_app import manager_app
from flask import jsonify, request

ec2_instance_ids = helper.populate_ec2_instances()

@manager_app.route("/invalidate_key", methods=['GET', 'POST'])
def invalidate_key():
    logging.info("Invalidating a key...")
    key = request.form['key']

    # TODO: Hash the key and send invalidate to proper node

    return jsonify({"status": "success", "status_code": 200})