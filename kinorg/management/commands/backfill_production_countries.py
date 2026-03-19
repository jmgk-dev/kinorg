import time

from django.core.management.base import BaseCommand

from kinorg.models import Film
from kinorg.views import get_tmdb_data


class Command(BaseCommand):
    help = 'Backfill production_countries and primary_country for all existing films'

    def handle(self, *args, **options):
        films = Film.objects.all()
        total = films.count()
        self.stdout.write(f'Backfilling {total} films...')

        updated = 0
        failed = 0

        for film in films:
            try:
                data = get_tmdb_data(
                    f'https://api.themoviedb.org/3/movie/{film.id}?language=en-US'
                )
                countries = data.get('production_countries', [])
                codes = [c['iso_3166_1'] for c in countries if 'iso_3166_1' in c]

                film.production_countries = countries
                film.primary_country = codes[0] if codes else ''
                film.save(update_fields=['production_countries', 'primary_country'])

                updated += 1
                self.stdout.write(f'  [{updated}/{total}] {film.title} → {codes}')

                time.sleep(0.25)  # stay within TMDB rate limits

            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  FAILED {film.title}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'Done. {updated} updated, {failed} failed.'
        ))
