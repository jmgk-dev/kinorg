from django.core.management.base import BaseCommand
from kinorg.models import Film
from kinorg.views import get_similar_films


class Command(BaseCommand):
    help = "Pre-compute similar_film_ids for every film in the DB."

    def add_arguments(self, parser):
        parser.add_argument(
            '--film-id',
            type=int,
            help='Only recompute for a single film (by TMDB ID)',
        )

    def handle(self, *args, **options):
        if options['film_id']:
            films = Film.objects.filter(id=options['film_id'])
        else:
            films = Film.objects.filter(release_date__isnull=False, poster_path__gt='')

        total = films.count()
        self.stdout.write(f"Computing similar films for {total} film(s)…")

        updated = 0
        for i, film in enumerate(films.iterator(), start=1):
            similar = get_similar_films(film.id, film, limit=12)
            film.similar_film_ids = [f.id for f in similar]
            film.save(update_fields=['similar_film_ids'])
            updated += 1
            if i % 100 == 0:
                self.stdout.write(f"  {i}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} film(s)."))
