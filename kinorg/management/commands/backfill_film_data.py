import time
from django.core.management.base import BaseCommand
from kinorg.models import Film
from kinorg.views import _import_film_from_tmdb


class Command(BaseCommand):
    help = "Backfill full TMDB data (cast, crew, genres, videos, providers) for films with minimal data."

    def add_arguments(self, parser):
        parser.add_argument(
            '--film-id',
            type=int,
            help='Only backfill a single film (by TMDB ID)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-import all films, not just those with minimal data',
        )

    def handle(self, *args, **options):
        if options['film_id']:
            films = Film.objects.filter(id=options['film_id'])
        elif options['all']:
            films = Film.objects.all()
        else:
            # Target films with minimal cast data (strings, not dicts)
            films = [
                f for f in Film.objects.all()
                if not f.cast or not isinstance((f.cast or [None])[0], dict)
            ]

        total = len(films) if isinstance(films, list) else films.count()
        self.stdout.write(f"Backfilling {total} film(s)…")

        updated = 0
        errors = 0
        for i, film in enumerate(films, start=1):
            try:
                _import_film_from_tmdb(film.id)
                updated += 1
                time.sleep(0.25)  # be polite to TMDB rate limits
            except Exception as e:
                self.stderr.write(f"  Error on film {film.id} ({film.title}): {e}")
                errors += 1

            if i % 50 == 0:
                self.stdout.write(f"  {i}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated}, errors {errors}."))
