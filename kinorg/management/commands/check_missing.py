"""
Read-only audit of all source lists vs the Film DB.
Outputs a CSV of every film that is either not findable on TMDB
or found on TMDB but not yet imported into the DB.
"""
import csv
import os
import time
from pathlib import Path

import openpyxl
import requests
import xlrd
from django.core.management.base import BaseCommand

from kinorg.models import Film

BASE_DIR = Path(__file__).parent

TMDB_SEARCH = "https://api.themoviedb.org/3/search/movie"


def tmdb_headers():
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {os.environ.get('TMDB_KEY', '')}",
    }


def search_tmdb(title, year):
    r = requests.get(TMDB_SEARCH, headers=tmdb_headers(), params={
        'query': title,
        'year': int(year),
        'language': 'en-US',
    }, timeout=10)
    results = r.json().get('results', [])
    return results[0] if results else None


# ---------------------------------------------------------------------------
# Parsers — each yields dicts with keys: position, title, year
# ---------------------------------------------------------------------------

def parse_letterboxd_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        first = f.readline()
        if first.startswith('Letterboxd list export'):
            f.readline()  # Date,Name,Tags,URL,Description
            f.readline()  # list metadata
            f.readline()  # blank line
        else:
            f.seek(0)
        for row in csv.DictReader(f):
            title = row.get('Name', '').strip()
            year = row.get('Year', '').strip()
            pos = row.get('Position', '').strip()
            if title and year:
                yield {'position': pos or '', 'title': title, 'year': int(str(year)[:4])}


def parse_tspdt_csv(path):
    """TSPDT direct export — columns: Pos, 2025, Title, Director, Year, ..."""
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            title = row.get('Title', '').strip()
            year = row.get('Year', '').strip()
            pos = row.get('Pos', '').strip()
            if title and year:
                yield {'position': pos or '', 'title': title, 'year': int(str(year)[:4])}


def parse_xlsx(path):
    """Sight & Sound 2022 XLSX — title=col2, year=col3, position=row number."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # header
        title = row[2]
        year = row[3]
        if title and year:
            try:
                yield {'position': str(i), 'title': str(title).strip(), 'year': int(str(year)[:4])}
            except (ValueError, TypeError):
                continue


def parse_xls(path):
    """TSPDT 1000 XLS — title=col3, year=col5, pos=col0."""
    wb = xlrd.open_workbook(path)
    ws = wb.sheet_by_index(0)
    for i in range(1, ws.nrows):
        row = ws.row_values(i)
        title = str(row[3]).strip() if row[3] else ''
        year = row[5]
        pos = row[0]
        if title and year:
            try:
                yield {'position': str(int(pos)) if pos else '', 'title': title, 'year': int(str(year)[:4])}
            except (ValueError, TypeError):
                continue


# ---------------------------------------------------------------------------
# Source definitions
# ---------------------------------------------------------------------------

SOURCES = [
    # (relative_path, collection_tag, parser_fn)
    ('collections/sight-and-sound-2022.xlsx',                             'sight_and_sound_2022',       parse_xlsx),
    ('collections/tspdt-100-greatest-films.xls',                          'tspdt_1000',                 parse_xls),
    ('collections/tspdt-the-21st-centurys-1000-most-acclaimed-films.csv', 'tspdt_21c',                  parse_tspdt_csv),
    ('collections/criterion.csv',                                          'criterion',                  parse_letterboxd_csv),
    ('collections/janus.csv',                                              'janus',                      parse_letterboxd_csv),
    ('collections/letterboxds-top-500-films-march26.csv',                  'letterboxd_top_500',         parse_letterboxd_csv),
    ('collections/oscar-winning-films-international-feature.csv',          'oscar_international_feature',parse_letterboxd_csv),
    ('collections/vinegar-syndrome-filmography.csv',                       'vinegar_syndrome',           parse_letterboxd_csv),
    ('lists/my-top-10-movies.csv',   None, parse_letterboxd_csv),
    ('lists/favorite-films.csv',     None, parse_letterboxd_csv),
    ('my_lists/liked-films.csv',     None, parse_letterboxd_csv),
    ('my_lists/yeah-these-ones.csv', None, parse_letterboxd_csv),
    ('my_lists/watchlist.csv',       None, parse_letterboxd_csv),
    ('my_lists/watched.csv',         None, parse_letterboxd_csv),
    ('my_lists/next-up.csv',         None, parse_letterboxd_csv),
]


class Command(BaseCommand):
    help = 'Audit all source lists against the Film DB and report missing films'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='missing_films_audit.csv',
            help='Path to write the missing films CSV (default: missing_films_audit.csv)',
        )

    def handle(self, *args, **options):
        missing = []

        for rel_path, collection_tag, parser_fn in SOURCES:
            full_path = BASE_DIR / rel_path
            if not full_path.exists():
                self.stderr.write(f"File not found, skipping: {rel_path}")
                continue

            filename = full_path.name
            self.stdout.write(f"\n{rel_path}")

            films = list(parser_fn(full_path))
            total = len(films)
            no_tmdb = 0
            not_in_db = 0

            for i, film in enumerate(films, 1):
                self.stdout.write(f"  [{i}/{total}] {film['title']} ({film['year']})", ending='\r')
                self.stdout.flush()

                try:
                    result = search_tmdb(film['title'], film['year'])
                    time.sleep(0.25)

                    if not result:
                        missing.append({
                            'source_file': rel_path,
                            'collection_tag': collection_tag or '',
                            'position': film['position'],
                            'title': film['title'],
                            'year': film['year'],
                            'tmdb_id': '',
                            'reason': 'No TMDB match',
                        })
                        no_tmdb += 1
                        continue

                    tmdb_id = result['id']
                    if not Film.objects.filter(pk=tmdb_id).exists():
                        missing.append({
                            'source_file': rel_path,
                            'collection_tag': collection_tag or '',
                            'position': film['position'],
                            'title': film['title'],
                            'year': film['year'],
                            'tmdb_id': tmdb_id,
                            'reason': 'Not in DB',
                        })
                        not_in_db += 1

                except Exception as e:
                    self.stderr.write(f"\n  Error on {film['title']}: {e}")

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f"  {total} checked — {no_tmdb} not on TMDB, {not_in_db} not in DB"
            ))

        output_path = options['output']
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'source_file', 'collection_tag', 'position', 'title', 'year', 'tmdb_id', 'reason'
            ])
            writer.writeheader()
            writer.writerows(missing)

        self.stdout.write(self.style.SUCCESS(
            f"\nAudit complete — {len(missing)} missing films written to: {output_path}"
        ))
