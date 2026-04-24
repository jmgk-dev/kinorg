import os
import requests
from django.core.management.base import BaseCommand
from kinorg.models import Film


class Command(BaseCommand):
    help = "Refresh GB watch providers for all films in the DB from TMDB."

    def add_arguments(self, parser):
        parser.add_argument(
            '--film-id',
            type=int,
            help='Only refresh for a single film (by TMDB ID)',
        )

    def handle(self, *args, **options):
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {os.environ.get('TMDB_KEY')}",
        }

        if options['film_id']:
            films = Film.objects.filter(id=options['film_id'])
        else:
            films = Film.objects.all()

        total = films.count()
        self.stdout.write(f"Refreshing watch providers for {total} film(s)…")

        updated = 0
        for i, film in enumerate(films.iterator(), start=1):
            try:
                url = f"https://api.themoviedb.org/3/movie/{film.id}/watch/providers"
                resp = requests.get(url, headers=headers, timeout=10)
                data = resp.json()
                film.watch_providers = data.get('results', {}).get('GB', {})
                film.save(update_fields=['watch_providers'])
                updated += 1
            except Exception as e:
                self.stderr.write(f"  Error on film {film.id}: {e}")

            if i % 100 == 0:
                self.stdout.write(f"  {i}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} film(s)."))
