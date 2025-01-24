import os
from datetime import date, timedelta

from .base import *

DEBUG = False

ALLOWED_HOSTS = ['kinorg.com', 'www.kinorg.com', '164.92.66.154']

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "OPTIONS": {
            "service": "kinorg",
        },
    }
}

# Bugsnag

BUGSNAG = {
    'api_key': 'e67ab4514492f52ffdc0c60270c6af28',
    'project_root': '/home/jamiek/kinorg',
}

