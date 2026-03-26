import csv
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from kinorg.models import Addition, Film, FilmList
from .tmdb_helpers import search_tmdb, fetch_tmdb_detail, build_defaults

BASE_DIR = Path(__file__).parent

COLLECTION_TAGS = {
    'tspdt-the-21st-centurys-1000-most-acclaimed-films.csv': 'tspdt_21c',
    'letterboxds-top-500-films-march26.csv': 'letterboxd_top_500',
    'oscar-winning-films-international-feature.csv': 'oscar_international_feature',
    'criterion.csv': 'criterion',
    'janus.csv': 'janus',
    'vinegar-syndrome-filmography.csv': 'vinegar_syndrome',
}

OWNER_USERNAME = 'jamie@jmgk.dev'


def parse_letterboxd_csv(csv_path):
    """Returns (list_name, rows). list_name is None for non-list-export formats."""
    list_name = None
    with open(csv_path, newline='', encoding='utf-8') as f:
        first_line = f.readline()
        if first_line.startswith('Letterboxd list export'):
            f.readline()  # Date,Name,Tags,URL,Description header
            meta = next(csv.reader([f.readline()]))
            list_name = meta[1].strip() if len(meta) > 1 else None
            f.readline()  # blank line
        else:
            f.seek(0)
        rows = list(csv.DictReader(f))
    return list_name, rows


class Command(BaseCommand):
    help = 'Import all Letterboxd CSVs from collections/, lists/, and my_lists/ folders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--missing-csv',
            type=str,
            default='missing_films.csv',
            help='Path to write missing films CSV (default: missing_films.csv)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            owner = User.objects.get(username=OWNER_USERNAME)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{OWNER_USERNAME}' not found"))
            return

        missing = []

        folders = [
            ('collections', BASE_DIR / 'collections'),
            ('lists',       BASE_DIR / 'lists'),
            ('my_lists',    BASE_DIR / 'my_lists'),
        ]

        for folder_name, folder_path in folders:
            csv_files = sorted(folder_path.glob('*.csv'))
            if not csv_files:
                self.stdout.write(f"No CSVs found in {folder_path}")
                continue

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {folder_name} ==="))

            for csv_path in csv_files:
                filename = csv_path.name
                collection_tag = COLLECTION_TAGS.get(filename) if folder_name == 'collections' else None

                list_name, rows = parse_letterboxd_csv(csv_path)

                film_list = None
                if folder_name == 'my_lists' and list_name:
                    try:
                        film_list = FilmList.objects.get(title__iexact=list_name, owner=owner)
                    except FilmList.DoesNotExist:
                        self.stderr.write(
                            f"  FilmList '{list_name}' not found for {OWNER_USERNAME} — skipping list linking"
                        )
                    except FilmList.MultipleObjectsReturned:
                        film_list = FilmList.objects.filter(title__iexact=list_name, owner=owner).first()

                created = updated = skipped = 0
                total = len(rows)
                self.stdout.write(f"\n{filename} ({total} films){f' → {collection_tag}' if collection_tag else ''}")

                for i, row in enumerate(rows, 1):
                    title = (row.get('Name') or row.get('Title') or '').strip()
                    year_raw = row.get('Year', '').strip()
                    rank = int(row.get('Position') or row.get('Pos') or 0)

                    if not title or not year_raw:
                        skipped += 1
                        continue

                    year_int = int(str(year_raw)[:4])

                    self.stdout.write(f"  [{i}/{total}] {title} ({year_int})", ending='\r')
                    self.stdout.flush()

                    try:
                        tmdb_id, media_type, prefetched = search_tmdb(title, year_int)
                        time.sleep(0.25)

                        if not tmdb_id:
                            self.stderr.write(f"\n  No TMDB match: {title} ({year_int})")
                            missing.append({
                                'folder': folder_name,
                                'file': filename,
                                'list_name': list_name or '',
                                'title': title,
                                'year': year_int,
                                'reason': 'No TMDB match',
                            })
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
                                missing.append({
                                    'folder': folder_name,
                                    'file': filename,
                                    'list_name': list_name or '',
                                    'title': title,
                                    'year': year_int,
                                    'reason': 'TMDB detail fetch failed',
                                })
                                skipped += 1
                                continue

                            defaults = build_defaults(data, media_type)
                            if collection_tag:
                                defaults['collections'] = [collection_tag]
                                if rank:
                                    defaults['collection_ranks'] = {collection_tag: rank}
                            film = Film.objects.create(id=tmdb_id, **defaults)
                            created += 1

                        if film_list and film:
                            Addition.objects.get_or_create(
                                film=film,
                                film_list=film_list,
                                defaults={'added_by': owner},
                            )

                    except Exception as e:
                        self.stderr.write(f"\n  Error on {title}: {e}")
                        missing.append({
                            'folder': folder_name,
                            'file': filename,
                            'list_name': list_name or '',
                            'title': title,
                            'year': year_int,
                            'reason': str(e),
                        })
                        skipped += 1

                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS(
                    f"  Done — {created} created, {updated} already in DB, {skipped} skipped"
                ))

        missing_path = options['missing_csv']
        with open(missing_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['folder', 'file', 'list_name', 'title', 'year', 'reason'])
            writer.writeheader()
            writer.writerows(missing)

        self.stdout.write(self.style.SUCCESS(
            f"\nMissing films written to: {missing_path} ({len(missing)} total)"
        ))
