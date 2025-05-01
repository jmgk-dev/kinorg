"""
WSGI config for collabproj project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Determine which settings to use based on DJANGO_ENV
django_env = os.getenv('DJANGO_ENV', 'development').lower()
if django_env == 'production':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_site.settings.prod')
elif django_env == 'development':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_site.settings.dev')
else:
    raise RuntimeError(f"Unknown DJANGO_ENV: {django_env}")

application = get_wsgi_application()
