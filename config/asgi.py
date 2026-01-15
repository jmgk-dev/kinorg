"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from dotenv import load_dotenv
load_dotenv()

# Determine which settings to use based on DJANGO_ENV
django_env = os.getenv('DJANGO_ENV', 'development').lower()
if django_env == 'production':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
elif django_env == 'development':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
else:
    raise RuntimeError(f"Unknown DJANGO_ENV: {django_env}")

application = get_asgi_application()
