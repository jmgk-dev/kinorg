import os
import re
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from kinorg.models import PCCScreening

PCC_URL = "https://princecharlescinema.com/whats-on/"
TMDB_ID_RE = re.compile(r"/film/(\d+)/")


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
        film_links = soup.select("a.liveeventtitle")

        seen = {}
        for a in film_links:
            href = a.get("href", "")
            match = TMDB_ID_RE.search(href)
            if match:
                tmdb_id = int(match.group(1))
                seen[tmdb_id] = href

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

        # Replace all existing records
        PCCScreening.objects.all().delete()
        PCCScreening.objects.bulk_create([
            PCCScreening(tmdb_id=tmdb_id, pcc_url=url)
            for tmdb_id, url in seen.items()
        ])

        self.stdout.write(self.style.SUCCESS(f"Done — {len(seen)} films saved."))
