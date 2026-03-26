import csv
import os
import time

import requests
from django.core.management.base import BaseCommand

from kinorg.models import Film

TMDB_SEARCH = "https://api.themoviedb.org/3/search/movie"
TMDB_DETAIL = "https://api.themoviedb.org/3/movie/{}"


def tmdb_headers():
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {os.environ.get('TMDB_KEY', '')}",
    }


def search_tmdb(title, year):
    r = requests.get(TMDB_SEARCH, headers=tmdb_headers(), params={
        'query': title,
        'year': int(year),
        'language': 'en-US',
    }, timeout=10)
    results = r.json().get('results', [])
    return results[0] if results else None


def fetch_tmdb_detail(tmdb_id):
    r = requests.get(
        TMDB_DETAIL.format(tmdb_id) + "?append_to_response=credits,keywords&language=en-US",
        headers=tmdb_headers(), timeout=10
    )
    return r.json() if r.status_code == 200 else None


def build_defaults(data):
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
    help = 'Import a Letterboxd list export CSV into the Film DB, optionally tagging a collection'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the Letterboxd CSV file')
        parser.add_argument(
            '--collection',
            type=str,
            default=None,
            help='Collection tag to apply to each film (e.g. criterion, letterboxd_top_500)',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        collection_tag = options['collection']

        with open(csv_path, newline='', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line.startswith('Letterboxd list export'):
                f.readline()  # Date,Name,Tags,URL,Description
                f.readline()  # list metadata row
                f.readline()  # blank line
            else:
                f.seek(0)

            rows = list(csv.DictReader(f))

        created = updated = skipped = 0
        total = len(rows)

        for i, row in enumerate(rows, 1):
            title = row.get('Name', '').strip()
            year_raw = row.get('Year', '').strip()

            if not title or not year_raw:
                skipped += 1
                continue

            year_int = int(str(year_raw)[:4])

            self.stdout.write(f"[{i}/{total}] {title} ({year_int})", ending='\r')
            self.stdout.flush()

            try:
                result = search_tmdb(title, year_int)
                time.sleep(0.25)

                if not result:
                    self.stderr.write(f"\nNo TMDB match: {title} ({year_int})")
                    skipped += 1
                    continue

                tmdb_id = result['id']
                film = Film.objects.filter(pk=tmdb_id).first()

                if film:
                    if collection_tag and collection_tag not in (film.collections or []):
                        film.collections = (film.collections or []) + [collection_tag]
                        film.save(update_fields=['collections'])
                    updated += 1
                else:
                    data = fetch_tmdb_detail(tmdb_id)
                    time.sleep(0.25)

                    if not data or not data.get('release_date'):
                        skipped += 1
                        continue

                    defaults = build_defaults(data)
                    if collection_tag:
                        defaults['collections'] = [collection_tag]
                    Film.objects.create(id=tmdb_id, **defaults)
                    created += 1

            except Exception as e:
                self.stderr.write(f"\nError on {title}: {e}")
                skipped += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"Done — {created} created, {updated} already in DB, {skipped} skipped."
        ))
