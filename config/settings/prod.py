import os
from datetime import date, timedelta

from .base import *

DEBUG = False

ALLOWED_HOSTS = ['kinorg.com', 'www.kinorg.com', '134.199.237.228']

SECRET_KEY = os.environ['DJANGO_SECURE_PRODUCTION_KEY']


# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get('DATABASE_NAME'),
        "USER": os.environ.get('DATABASE_USER'),
        "PASSWORD": os.environ.get('DATABASE_PASSWORD'),
        "HOST": os.environ.get('DATABASE_HOST'),
        "PORT": os.environ.get('DATABASE_PORT'),
    }
}

# Email

ANYMAIL = {
    "MAILGUN_API_KEY": os.environ['MAILGUN_API_KEY'],
}


EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
DEFAULT_FROM_EMAIL = 'Kinorg Admin <admin@kinorg.com>'
SERVER_EMAIL = 'Kinorg Server <server@kinorg.com>'


# Bugsnag

BUGSNAG = {
    'api_key': os.environ['BUGSNAG_API_KEY'],
    'project_root': os.environ['PATH_TO_YOUR_APP'],
}

# Cache

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": "127.0.0.1:11211",
    }
}