import os
import re
import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from kinorg.models import Film, PCCScreening
from .tmdb_helpers import search_tmdb, fetch_tmdb_detail, build_defaults

PCC_URL = "https://princecharlescinema.com/whats-on/"
YEAR_RE = re.compile(r"\((\d{4})\)$")
SPAN_YEAR_RE = re.compile(r"^\d{4}$")


def extract_title_and_year(a_tag, runtime_div):
    raw_title = a_tag.get_text(strip=True)

    # Try to get year from running-time spans first
    year = None
    if runtime_div:
        for span in runtime_div.select("span"):
            text = span.get_text(strip=True)
            if SPAN_YEAR_RE.match(text):
                year = int(text)
                break

    # Fall back to year embedded in title e.g. "The Killer (1989)"
    if not year:
        m = YEAR_RE.search(raw_title)
        if m:
            year = int(m.group(1))

    # Strip parenthetical year from title
    clean_title = YEAR_RE.sub("", raw_title).strip()

    return clean_title, year


class Command(BaseCommand):
    help = "Scrape Prince Charles Cinema what's on page and update PCCScreening table"

    def handle(self, *args, **options):
        self.stdout.write("Fetching PCC programme...")
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; Kinorg/1.0)"}
            response = requests.get(PCC_URL, timeout=10, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(f"Failed to fetch PCC page: {e}")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        seen = {}
        for film in soup.select(".film_list-outer"):
            a = film.select_one("a.liveeventtitle")
            runtime_div = film.select_one(".running-time")
            if not a:
                continue
            href = a.get("href", "")
            title, year = extract_title_and_year(a, runtime_div)
            if title and href:
                seen[(title, year)] = href

        if not seen:
            self.stderr.write("No films found — PCC page structure may have changed.")
            admin_email = os.environ.get("ADMIN_EMAIL")
            if admin_email:
                send_mail(
                    subject="[Kinorg] PCC scraper found 0 films",
                    message=(
                        "The PCC scraper ran but found no films.\n\n"
                        "The Prince Charles Cinema website may have changed its HTML structure.\n\n"
                        f"Check: {PCC_URL}"
                    ),
                    from_email=None,
                    recipient_list=[admin_email],
                )
            return

        seen_urls = set()
        for (title, year), url in seen.items():
            _, created = PCCScreening.objects.update_or_create(
                pcc_url=url,
                defaults={'title': title, 'year': year},
            )
            if created:
                PCCScreening.objects.filter(pcc_url=url).update(hidden=True)
            seen_urls.add(url)

        # Remove screenings no longer on the PCC page (but preserve hidden/manual ones)
        PCCScreening.objects.exclude(pcc_url__in=seen_urls).delete()

        self.stdout.write(self.style.SUCCESS(f"{len(seen)} screenings saved."))

        # Import any films not already in the DB
        self.stdout.write("Importing missing films from TMDB...")
        imported = skipped = 0

        for (title, year), _ in seen.items():
            if not year:
                continue  # can't search TMDB reliably without a year

            if Film.objects.filter(title__iexact=title).exists():
                continue  # already in DB

            try:
                tmdb_id, media_type, prefetched = search_tmdb(title, year)
                time.sleep(0.25)

                if not tmdb_id:
                    self.stderr.write(f"No TMDB match: {title} ({year})")
                    skipped += 1
                    continue

                if Film.objects.filter(pk=tmdb_id).exists():
                    continue  # in DB under a different title

                data = prefetched or fetch_tmdb_detail(tmdb_id, media_type)
                if not prefetched:
                    time.sleep(0.25)

                if not data or not data.get('release_date'):
                    skipped += 1
                    continue

                defaults = build_defaults(data, media_type)
                Film.objects.create(id=tmdb_id, **defaults)
                imported += 1
                self.stdout.write(f"  Imported: {title} ({year})")

            except Exception as e:
                self.stderr.write(f"Error importing {title}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Done — {imported} films imported, {skipped} skipped."
        ))

        # Auto-link screenings to Film records by title match (don't overwrite manual links)
        self.stdout.write("Auto-linking screenings to films...")
        unlinked = PCCScreening.objects.filter(film__isnull=True)
        linked = 0
        for screening in unlinked:
            qs = Film.objects.filter(title__iexact=screening.title)
            if screening.year:
                film = qs.filter(release_date__year=screening.year).first() or qs.first()
            else:
                film = qs.first()
            if film:
                screening.film = film
                screening.hidden = False
                screening.save(update_fields=['film', 'hidden'])
                linked += 1
        self.stdout.write(self.style.SUCCESS(f"Linked {linked} screenings."))
