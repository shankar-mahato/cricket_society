# PythonAnywhere WSGI Configuration File
# Copy this content to your PythonAnywhere WSGI configuration file
# Path: /var/www/cricketsociety_pythonanywhere_com_wsgi.py

# +++++++++++ DJANGO +++++++++++
# To use your own Django app use code like this:
import os
import sys

# ===== UPDATE THESE PATHS TO MATCH YOUR SETUP =====
# Project root directory (where requirements.txt is)
project_home = '/home/cricketsociety/cricket_society'

# Django project directory (where manage.py is)
mycricket_path = '/home/cricketsociety/cricket_society/mycricket'
# ==================================================

# Add project directory to Python path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Add Django project directory to Python path
if mycricket_path not in sys.path:
    sys.path.insert(0, mycricket_path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'

# Change to the Django project directory
os.chdir(mycricket_path)

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()




