from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, IntegerField, RadioField, BooleanField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from wtforms.validators import DataRequired, InputRequired

import aws_helper

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
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm_password', message='Passwords must match')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    status = SelectField('Status', choices=[('0', 'Employee'), ('1', 'Customer'), ('2', 'Admin')], coerce=int)
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = aws_helper.dynamo_get_user(email.data)
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    status = SelectField('Status', choices=[('0', 'Employee'), ('1', 'Customer'), ('2', 'Admin')], coerce=int)
    submit = SubmitField('Log In')


