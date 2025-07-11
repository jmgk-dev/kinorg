import os
from datetime import date, timedelta

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

print("Using development settings (dev.py)")

SECRET_KEY = os.getenv('DJANGO_DEV_KEY')

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}



