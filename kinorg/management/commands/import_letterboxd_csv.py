import csv
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from kinorg.models import Film
from .tmdb_helpers import search_tmdb, fetch_tmdb_detail, build_defaults


def parse_letterboxd_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        first_line = f.readline()
        if first_line.startswith('Letterboxd list export'):
            f.readline()  # Date,Name,Tags,URL,Description
            f.readline()  # list metadata row
            f.readline()  # blank line
        else:
            f.seek(0)
        return list(csv.DictReader(f))


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
        rows = parse_letterboxd_csv(csv_path)

        created = updated = skipped = 0
        total = len(rows)

        for i, row in enumerate(rows, 1):
            title = row.get('Name', '').strip()
            year_raw = row.get('Year', '').strip()
            rank = int(row.get('Position', 0) or 0)

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
                    if collection_tag and collection_tag not in (film.collections or []):
                        film.collections = (film.collections or []) + [collection_tag]
                        changed.append('collections')
                    if collection_tag and rank and film.collection_ranks.get(collection_tag) != rank:
                        film.collection_ranks = {**(film.collection_ranks or {}), collection_tag: rank}
                        changed.append('collection_ranks')
                    if changed:
                        film.save(update_fields=changed)
                    updated += 1
                else:
                    if prefetched:
                        data = prefetched
                    else:
                        data = fetch_tmdb_detail(tmdb_id, media_type)
                        time.sleep(0.25)

                    if not data or not data.get('release_date'):
                        skipped += 1
                        continue

                    defaults = build_defaults(data, media_type)
                    if collection_tag:
                        defaults['collections'] = [collection_tag]
                        if rank:
                            defaults['collection_ranks'] = {collection_tag: rank}
                    Film.objects.create(id=tmdb_id, **defaults)
                    created += 1

            except Exception as e:
                self.stderr.write(f"\nError on {title}: {e}")
                skipped += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"Done — {created} created, {updated} already in DB, {skipped} skipped."
        ))
