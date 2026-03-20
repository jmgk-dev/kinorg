import os
import re
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from kinorg.models import PCCScreening

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

        PCCScreening.objects.all().delete()
        PCCScreening.objects.bulk_create([
            PCCScreening(title=title, year=year, pcc_url=url)
            for (title, year), url in seen.items()
        ])

        self.stdout.write(self.style.SUCCESS(f"Done — {len(seen)} films saved."))
