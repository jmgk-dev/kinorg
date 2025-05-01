import os
from datetime import date, timedelta
from django.core.management.utils import get_random_secret_key

from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

print("Using development settings")

SECRET_KEY = os.getenv('DJANGO_DEV_KEY', get_random_secret_key())


