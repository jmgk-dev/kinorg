import os
import time

from django.core.management.base import BaseCommand

from kinorg.views import get_tmdb_data
from film_games.models import GameFilm


class Command(BaseCommand):
    help = 'Fetch well-known films from TMDB top-rated list and add to the GameFilm pool (unapproved)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            type=int,
            default=20,
            help='Number of TMDB pages to fetch (20 results per page)',
        )
        parser.add_argument(
            '--min-votes',
            type=int,
            default=5000,
            help='Minimum vote_count to include a film',
        )
        parser.add_argument(
            '--min-year',
            type=int,
            default=1950,
            help='Earliest release year to include',
        )

    def handle(self, *args, **options):
        pages = options['pages']
        min_votes = options['min_votes']
        min_year = options['min_year']

        added = 0
        skipped = 0
        existing = 0

        for page in range(1, pages + 1):
            self.stdout.write(f'Fetching page {page}/{pages}...')
            data = get_tmdb_data(
                f'https://api.themoviedb.org/3/movie/top_rated?language=en-US&page={page}'
            )
            results = data.get('results', [])

            for film in results:
                vote_count = film.get('vote_count', 0)
                release_date = film.get('release_date', '')
                year = int(release_date[:4]) if release_date and len(release_date) >= 4 else 0

                if vote_count < min_votes:
                    skipped += 1
                    continue
                if year < min_year:
                    skipped += 1
                    continue

                _, created = GameFilm.objects.get_or_create(
                    tmdb_id=film['id'],
                    defaults={
                        'title': film.get('title', ''),
                        'release_date': release_date,
                        'poster_path': film.get('poster_path', ''),
                        'vote_count': vote_count,
                        'approved': False,
                    }
                )

                if created:
                    added += 1
                    self.stdout.write(f'  + {film["title"]} ({year}) — {vote_count:,} votes')
                else:
                    existing += 1

            time.sleep(0.25)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {added} added, {existing} already existed, {skipped} skipped.'
        ))
