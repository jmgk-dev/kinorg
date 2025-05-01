import os
from datetime import date, timedelta

from .base import *

DEBUG = False

ALLOWED_HOSTS = ['kinorg.com', 'www.kinorg.com', '164.92.66.154']

print("Using production settings")

SECRET_KEY = os.environ['DJANGO_SECURE_PRODUCTION_KEY']

# Bugsnag

# BUGSNAG = {
#     'api_key': os.environ['BUGSNAG_API_KEY'],
#     'project_root': os.environ['PATH_TO_YOUR_APP'],
# }



