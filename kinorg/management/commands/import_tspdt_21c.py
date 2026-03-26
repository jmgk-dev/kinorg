import csv
import os
import time

from django.core.management.base import BaseCommand

from kinorg.models import Film
from .tmdb_helpers import search_tmdb, fetch_tmdb_detail, build_defaults

COLLECTION_TAG = 'tspdt_21c'
CSV_PATH = os.path.join(os.path.dirname(__file__), 'TSPDT - The 21st Centurys 1000 Most Acclaimed Films.csv')


class Command(BaseCommand):
    help = "Import TSPDT 21st Century's 1000 Most Acclaimed Films into the Film DB"

    def handle(self, *args, **options):
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        created = updated = skipped = 0
        total = len(rows)

        for i, row in enumerate(rows, 1):
            title = row.get('Title', '').strip()
            year_raw = row.get('Year', '').strip()
            rank = int(str(row.get('Pos', 0) or 0)[:4] or 0)

            if not title or not year_raw:
                skipped += 1
                continue

            year_int = int(str(year_raw)[:4])

            self.stdout.write(f"[{i}/{total}] {title} ({year_int})", ending='\r')
            self.stdout.flush()

            try:
                tmdb_id, media_type, prefetched = search_tmdb(title, year_int)
                time.sleep(0.25)

                if not tmdb_id:
                    self.stderr.write(f"\nNo TMDB match: {title} ({year_int})")
                    skipped += 1
                    continue

                film = Film.objects.filter(pk=tmdb_id).first()

                if film:
                    changed = []
                    if COLLECTION_TAG not in (film.collections or []):
                        film.collections = (film.collections or []) + [COLLECTION_TAG]
                        changed.append('collections')
                    if rank and film.collection_ranks.get(COLLECTION_TAG) != rank:
                        film.collection_ranks = {**(film.collection_ranks or {}), COLLECTION_TAG: rank}
                        changed.append('collection_ranks')
                    if changed:
                        film.save(update_fields=changed)
                    updated += 1
                else:
                    data = prefetched or fetch_tmdb_detail(tmdb_id, media_type)
                    if not prefetched:
                        time.sleep(0.25)

                    if not data or not data.get('release_date'):
                        skipped += 1
                        continue

                    defaults = build_defaults(data, media_type)
                    defaults['collections'] = [COLLECTION_TAG]
                    if rank:
                        defaults['collection_ranks'] = {COLLECTION_TAG: rank}
                    Film.objects.create(id=tmdb_id, **defaults)
                    created += 1

            except Exception as e:
                self.stderr.write(f"\nError on {title}: {e}")
                skipped += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"Done — {created} created, {updated} tagged, {skipped} skipped."
        ))
