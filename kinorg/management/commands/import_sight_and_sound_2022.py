import os
import time

import openpyxl
from django.core.management.base import BaseCommand

from kinorg.models import Film
from .tmdb_helpers import search_tmdb, fetch_tmdb_detail, build_defaults

COLLECTION_TAG = 'sight_and_sound_2022'
XLSX_PATH = os.path.join(os.path.dirname(__file__), 'Sight and Sound 2022.xlsx')


class Command(BaseCommand):
    help = "Import Sight & Sound 2022 Greatest Films poll into the Film DB"

    def handle(self, *args, **options):
        wb = openpyxl.load_workbook(XLSX_PATH)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        total = len(rows) - 1

        created = updated = skipped = 0

        for i, row in enumerate(rows[1:], start=1):
            title = row[2]
            year = row[3]
            rank = i

            if not title or not year:
                skipped += 1
                continue

            self.stdout.write(f"[{i}/{total}] {title} ({int(year)})", ending='\r')
            self.stdout.flush()

            try:
                tmdb_id, media_type, prefetched = search_tmdb(title, year)
                time.sleep(0.25)

                if not tmdb_id:
                    self.stderr.write(f"\nNo TMDB match: {title} ({int(year)})")
                    skipped += 1
                    continue

                film = Film.objects.filter(pk=tmdb_id).first()

                if film:
                    changed = []
                    if COLLECTION_TAG not in (film.collections or []):
                        film.collections = (film.collections or []) + [COLLECTION_TAG]
                        changed.append('collections')
                    if film.collection_ranks.get(COLLECTION_TAG) != rank:
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
