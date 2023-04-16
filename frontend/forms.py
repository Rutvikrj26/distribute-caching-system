from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, IntegerField, RadioField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from wtforms.validators import DataRequired, InputRequired
from frontend.models import User

class UploadForm(FlaskForm):
    # Define the form here to upload a key/value pair
    key = StringField('Enter a unique key:', validators=[DataRequired()])
    customer = StringField("Enter the customer's e-mail address:", validators=[DataRequired()])
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

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


