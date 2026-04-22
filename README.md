# Kinorg

A social film tracker built with Django. Create lists, invite collaborators, log watched films with star ratings and reviews, and discover what's playing at certain UK cinemas.

Live at [kinorg.com](https://kinorg.com).

## Features

- Film data pulled from [TMDB](https://www.themoviedb.org/)
- Personal watchlist, liked films, and watched log
- Mini-reviews (280 chars) with 1-5 star ratings
- Collaborative film lists — invite other users as guests
- Curated collections: TSPDT 1000, TSPDT 21st Century, Sight & Sound 2022, Letterboxd Top 500, Criterion, Janus, Oscar International Feature, Vinegar Syndrome
- UK cinema listings integration — daily scrape of what's on
- Similar films (pre-computed weekly)

## Tech stack

- Django 6.0, Python 3.12+
- PostgreSQL
- Memcached (production caching)
- django-q2 for background tasks
- Vanilla JavaScript (no frontend framework)
- Plain CSS (no utility framework)
- whitenoise for static files
- django-anymail + Mailgun for transactional email
- bugsnag for error tracking

## Running locally

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- A [TMDB API key](https://www.themoviedb.org/settings/api)

### Setup

```bash
# Clone
git clone git@github.com:jmgk-dev/kinorg.git
cd kinorg

# Create a virtualenv and install deps
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy env file and fill in your values
cp .env.example .env
# edit .env with your TMDB key, DB credentials etc.

# Create the database
createdb kinorg_dev

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the dev server
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000).

## Running tests

```bash
python manage.py test kinorg
```

## Management commands

Useful commands for populating data:

```bash
# Import curated collections (requires CSV/Excel files — see the command source)
python manage.py import_tspdt_1000
python manage.py import_tspdt_21c
python manage.py import_sight_and_sound_2022
python manage.py import_all_csvs

# Compute similar films (runs weekly in production)
python manage.py compute_similar_films

# Scrape cinema listings
python manage.py scrape_pcc

# Refresh TMDB watch provider data
python manage.py refresh_watch_providers
```

## Project structure

```
kinorg/              — main app (films, lists, reviews, cinema integration)
user_admin/          — custom user model
config/settings/     — split settings (base, dev, prod)
staticfiles/css/     — global CSS (source)
kinorg/static/       — per-app JS and CSS (source)
static/              — collectstatic output (gitignored in dev)
```

## License

See [LICENSE](LICENSE).
