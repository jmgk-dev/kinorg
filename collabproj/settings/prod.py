import os
from datetime import date, timedelta

from .base import *

DEBUG = False

ALLOWED_HOSTS = ['kinorg.com', 'www.kinorg.com']

print("Using production settings")

SECRET_KEY = os.environ['DJANGO_SECURE_PRODUCTION_KEY']

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

# EMAIL_BACKEND

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ['EMAIL_HOST_URL']
EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_USE_TLS = True
EMAIL_PORT = 2525
DEFAULT_FROM_EMAIL = 'Password Reset <passwordreset@jmgk.dev>'

# Bugsnag

BUGSNAG = {
    'api_key': os.environ['BUGSNAG_API_KEY'],
    'project_root': os.environ['PATH_TO_YOUR_APP'],
}



