import os
import re
import time
import requests
from django.core.management.base import BaseCommand
from kinorg.models import Film

COLLECTION_TAG = 'letterboxd_top_500'
LIST_URL = "https://letterboxd.com/official/list/letterboxds-top-500-films/detail/page/{}/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Kinorg/1.0)"}
TMDB_ID_RE = re.compile(r'themoviedb\.org/movie/(\d+)')
SLUG_RE = re.compile(r'data-film-slug="([^"]+)"')
TMDB_BASE = "https://api.themoviedb.org/3/movie/{}"


def get_tmdb_headers():
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {os.environ.get('TMDB_KEY', '')}",
    }


def fetch_slugs():
    slugs = []
    for page in range(1, 6):
        url = LIST_URL.format(page)
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            break
        found = SLUG_RE.findall(r.text)
        slugs.extend(found)
        time.sleep(0.5)
    return slugs


def get_tmdb_id(slug):
    url = f"https://letterboxd.com/film/{slug}/"
    r = requests.get(url, headers=HEADERS, timeout=10)
    match = TMDB_ID_RE.search(r.text)
    return int(match.group(1)) if match else None


def fetch_tmdb_film(tmdb_id):
    url = TMDB_BASE.format(tmdb_id) + "?append_to_response=credits,keywords&language=en-US"
    r = requests.get(url, headers=get_tmdb_headers(), timeout=10)
    if r.status_code != 200:
        return None
    return r.json()


def build_film_defaults(data):
    crew = data.get('credits', {}).get('crew', [])
    cast = data.get('credits', {}).get('cast', [])
    keywords = data.get('keywords', {}).get('keywords', [])
    countries = [c['iso_3166_1'] for c in data.get('production_countries', [])]
    return {
        'title': data.get('title', ''),
        'release_date': data.get('release_date') or None,
        'poster_path': data.get('poster_path', '') or '',
        'backdrop_path': data.get('backdrop_path', '') or '',
        'overview': data.get('overview', ''),
        'genres': [g['name'] for g in data.get('genres', [])],
        'cast': [a['name'] for a in cast[:5]],
        'crew': [{'name': c['name'], 'job': c['job']} for c in crew if c['job'] in ('Director', 'Screenplay', 'Writer')],
        'keywords': [k['name'] for k in keywords],
        'runtime': data.get('runtime'),
        'production_companies': [c['name'] for c in data.get('production_companies', [])[:3]],
        'production_countries': countries,
        'primary_country': countries[0] if countries else '',
    }


class Command(BaseCommand):
    help = "Scrape Letterboxd Top 500 and populate Film DB with collection tag"

    def handle(self, *args, **options):
        self.stdout.write("Fetching film slugs from Letterboxd...")
        slugs = fetch_slugs()
        self.stdout.write(f"Found {len(slugs)} slugs. Processing...")

        created = updated = skipped = 0

        for i, slug in enumerate(slugs, 1):
            self.stdout.write(f"[{i}/{len(slugs)}] {slug}", ending='\r')
            self.stdout.flush()

            try:
                tmdb_id = get_tmdb_id(slug)
                time.sleep(0.3)

                if not tmdb_id:
                    skipped += 1
                    continue

                film = Film.objects.filter(pk=tmdb_id).first()

                if film:
                    # Already in DB — just ensure collection tag is present
                    if COLLECTION_TAG not in film.collections:
                        film.collections = film.collections + [COLLECTION_TAG]
                        film.save(update_fields=['collections'])
                    updated += 1
                else:
                    # Fetch from TMDB and create
                    data = fetch_tmdb_film(tmdb_id)
                    time.sleep(0.3)

                    if not data or not data.get('release_date'):
                        skipped += 1
                        continue

                    defaults = build_film_defaults(data)
                    defaults['collections'] = [COLLECTION_TAG]

                    Film.objects.create(id=tmdb_id, **defaults)
                    created += 1

            except Exception as e:
                self.stderr.write(f"\nError on {slug}: {e}")
                skipped += 1
                continue

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"Done — {created} created, {updated} tagged, {skipped} skipped."
        ))
