import os
from datetime import date, timedelta

from .base import *

DEBUG = False

ALLOWED_HOSTS = ['kinorg.com', 'www.kinorg.com']

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "OPTIONS": {
            "service": "kinorg",
        },
    }
}



