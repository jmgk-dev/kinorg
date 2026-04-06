import os
from datetime import date, timedelta

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SECRET_KEY = os.getenv('DJANGO_DEV_KEY')


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kinorg_dev',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

