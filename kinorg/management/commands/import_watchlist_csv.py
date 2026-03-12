import csv
import time

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from kinorg.models import Film, FilmList, Addition
from kinorg.views import get_tmdb_data


class Command(BaseCommand):
    help = 'Import a Letterboxd CSV (watchlist or list export) into a FilmList'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file')
        parser.add_argument('username', type=str, help='Username to assign the list to')
        parser.add_argument('list_title', type=str, help='Title for the new FilmList')

    def handle(self, *args, **options):
        User = get_user_model()

        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User '{options['username']}' not found"))
            return

        film_list, created = FilmList.objects.get_or_create(
            title=options['list_title'],
            owner=user,
        )
        self.stdout.write(f"{'Created' if created else 'Using existing'} list: {film_list.title}")

        imported, skipped, failed = 0, 0, 0

        with open(options['csv_path'], newline='', encoding='utf-8') as f:

            first_line = f.readline()
            if first_line.startswith('Letterboxd list export'):
                self.stdout.write('Detected format: list export')
                f.readline()  # Date,Name,Tags,URL,Description
                f.readline()  # 2024-02-27,Yeah these ones,... (list metadata)
                f.readline()  # blank line
            else:
                self.stdout.write('Detected format: watchlist')
                f.seek(0)

            reader = csv.DictReader(f)

            for row in reader:
                title = row.get('Name', '').strip()
                year = row.get('Year', '').strip()

                if not title or not year:
                    continue

                # Search TMDB by title + year
                search_data = get_tmdb_data(
                    f"https://api.themoviedb.org/3/search/movie"
                    f"?query={title}&primary_release_year={year}"
                    f"&include_adult=false&language=en-US&page=1"
                )

                results = search_data.get('results', [])

                if not results:
                    self.stdout.write(self.style.WARNING(f"  Not found: {title} ({year})"))
                    failed += 1
                    continue

                tmdb_id = results[0]['id']

                # Skip if already in this list
                if Addition.objects.filter(film_id=tmdb_id, film_list=film_list).exists():
                    self.stdout.write(f"  Skipped (already in list): {title}")
                    skipped += 1
                    continue

                # Fetch full film data
                full_data = get_tmdb_data(
                    f"https://api.themoviedb.org/3/movie/{tmdb_id}"
                    f"?append_to_response=credits,keywords&language=en-US"
                )

                release_date = full_data.get('release_date') or f"{year}-01-01"

                film, _ = Film.objects.update_or_create(
                    id=tmdb_id,
                    defaults={
                        'title':                full_data.get('title', title),
                        'release_date':         release_date,
                        'poster_path':   full_data.get('poster_path') or '',
                        'backdrop_path': full_data.get('backdrop_path') or '',
                        'overview':             full_data.get('overview', ''),
                        'runtime':              full_data.get('runtime'),
                        'cast':                 full_data.get('credits', {}).get('cast', []),
                        'crew':                 full_data.get('credits', {}).get('crew', []),
                        'genres':               full_data.get('genres', []),
                        'keywords':             full_data.get('keywords', {}).get('keywords', []),
                        'production_companies': full_data.get('production_companies', []),
                    }
                )

                Addition.objects.get_or_create(
                    film=film,
                    film_list=film_list,
                    defaults={'added_by': user}
                )

                self.stdout.write(f"  ✓ {title} ({year})")
                imported += 1

                time.sleep(0.25)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {imported} imported, {skipped} already in list, {failed} not found on TMDB"
        ))