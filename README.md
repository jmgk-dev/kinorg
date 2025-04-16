# Kinorg

## Description
Create film watchlists and invite other users to collaborate. Data pulled in via the TMDB API.

## Table of Contents
1. [Installation](#installation)
2. [Usage](#usage)
3. [Contact Information](#contact-information)

## Installation
Provide step-by-step instructions on how to get the development environment running.

# Clone the repo
```bash
git clone https://github.com/jmgk-dev/kinorg.git
```

# Navigate to the project directory
```bash
cd kinorg
```

# Create a virtual environment
```bash
python3 -m venv venv
```

# Activate the virtual environment
```bash
source venv/bin/activate
```

# Install dependencies
```bash
pip install -r requirements.txt
```

# Create a secret keys for development and production to a new .env
```bash
echo "DJANGO_DEV_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" >> .env && \
echo "DJANGO_SECURE_PRODUCTION_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" >> .env
```

# Migrate the database
```bash
python manage.py migrate
```

# Start the development server
```bash
python manage.py runserver
```

# Create superuser
```bash
python manage.py createsuperuser
```


## Usage
Instructions on how to use the project.
```bash
# Example of how to use the project
```


## Contact Information
```
jamie@jmgk.dev
```

