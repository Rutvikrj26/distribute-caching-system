from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, IntegerField, RadioField, BooleanField
from wtforms.validators import DataRequired, InputRequired
from frontend.models import Image


class UploadForm(FlaskForm):
    # Define the form here to upload a key/value pair
    key = StringField('Enter a unique key:', validators=[DataRequired()])
    value = FileField('Browse:', validators=[DataRequired()])
    submit = SubmitField('Submit')


class DisplayForm(FlaskForm):
    # Define the form here to retrieve a value based on a given key
    key = StringField('Enter a unique key:', validators=[DataRequired()])
    submit = SubmitField('Submit')


class MemcacheConfigForm(FlaskForm):
    # Define the form here to change memcache configuration
    capacity = IntegerField('Memcache capacity (in MB):', validators=[InputRequired()])
    clear_cache = BooleanField('Clear All Keys from Cache?')
    submit = SubmitField('Submit')


class SubmitButton(FlaskForm):
    # Button to delete all images and keys from the program
    submit = SubmitField('Delete All Keys and Images')

