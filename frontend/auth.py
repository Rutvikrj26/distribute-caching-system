# import boto3
# from flask import flash, redirect, url_for
# from flask_login import UserMixin, LoginManager, login_required
#
# dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
# table = dynamodb.Table('users')  # Replace 'users' with the name of your table
#
# login_manager = LoginManager()
#
# class User(UserMixin):
#     def __init__(self, email, password, is_employee, is_admin):
#         self.email = email
#         self.password = password
#         self.is_employee = is_employee
#         self.is_admin = is_admin
#
#     def get_id(self):
#         return self.email
#
# def user_loader(email):
#     response = table.get_item(Key={'email': email})
#     if 'Item' not in response:
#         return None
#     user_data = response['Item']
#     return User(email=user_data['email'])
#
# @login_manager.user_loader
# def load_user(email):
#     return user_loader(email)
#
# current_user = login_manager.user_loader
#
# # Extra Decorator to identify if the user logged in is employee or not
# def employee_login_required(f):
#     @login_required
#     def decorated_function(*args, **kwargs):
#         if current_user.is_employee:
#             return f(*args, **kwargs)
#         else:
#             flash('You do not have access to this page.', 'danger')
#             return redirect(url_for('index'))
#     return decorated_function
#
# def admin_login_required(f):
#     @login_required
#     def decorated_function(*args, **kwargs):
#         if current_user.is_admin:
#             return f(*args, **kwargs)
#         else:
#             flash('You do not have access to this page.', 'danger')
#             return redirect(url_for('index'))
#     return decorated_function