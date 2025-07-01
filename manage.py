#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from dotenv import load_dotenv
load_dotenv()

def main():
    """Run administrative tasks."""

    # Determine which settings to use based on DJANGO_ENV
    django_env = os.getenv('DJANGO_ENV', 'development').lower()
    if django_env == 'production':
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collabproj.settings.prod')
    elif django_env == 'development':
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collabproj.settings.dev')
    else:
        raise RuntimeError(f"Unknown DJANGO_ENV: {django_env}")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
