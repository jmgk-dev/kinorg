import os
import re
import requests
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

from .models import Film, FilmList, Addition


def import_letterboxd_list(letterboxd_username, letterboxd_list_slug, film_list_id, user_id):
    """
    Background task: scrape a Letterboxd list and import films into a FilmList.
    Sends an email to the user when complete.
    """
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    film_list = FilmList.objects.get(pk=film_list_id)

    headers = {"User-Agent": "Mozilla/5.0"}
    imported_count = 0
    failed_count = 0

    # Step 1 — scrape the list page(s)
    page = 1
    slugs = []

    while True:
        url = f"https://letterboxd.com/{letterboxd_username}/list/{letterboxd_list_slug}/page/{page}/"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            break

        # Extract all film slugs from the page
        found = re.findall(r'data-film-slug="([^"]+)"', response.text)

        if not found:
            break  # no more pages

        slugs.extend(found)
        page += 1

    # Step 2 — for each slug, get TMDB ID from the film page
    for slug in slugs:
        try:
            film_url = f"https://letterboxd.com/film/{slug}/"
            film_response = requests.get(film_url, headers=headers)

            match = re.search(r'themoviedb\.org/movie/(\d+)', film_response.text)
            if not match:
                failed_count += 1
                continue

            tmdb_id = int(match.group(1))

            # Step 3 — fetch full data from TMDB (reuses same pattern as add_film)
            tmdb_response = requests.get(
                f"https://api.themoviedb.org/3/movie/{tmdb_id}"
                f"?append_to_response=credits,keywords&language=en-US",
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {os.environ.get('TMDB_KEY')}"
                }
            )
            full_data = tmdb_response.json()

            film_object, _ = Film.objects.update_or_create(
                id=tmdb_id,
                defaults={
                    'title': full_data.get('title', ''),
                    'release_date': full_data.get('release_date'),
                    'poster_path': full_data.get('poster_path', ''),
                    'overview': full_data.get('overview', ''),
                    'genres': [g['name'] for g in full_data.get('genres', [])],
                    'director': [c['name'] for c in full_data.get('credits', {}).get('crew', []) if c['job'] == 'Director'],
                    'cast': [a['name'] for a in full_data.get('credits', {}).get('cast', [])[:5]],
                    'keywords': [k['name'] for k in full_data.get('keywords', {}).get('keywords', [])],
                    'runtime': full_data.get('runtime'),
                    'tmdb_vote_average': full_data.get('vote_average'),
                    'tmdb_vote_count': full_data.get('vote_count', 0),
                    'original_language': full_data.get('original_language', ''),
                    'production_companies': [c['name'] for c in full_data.get('production_companies', [])[:3]],
                }
            )

            Addition.objects.get_or_create(
                film=film_object,
                film_list=film_list,
                defaults={'added_by': user}
            )

            imported_count += 1

        except Exception:
            failed_count += 1
            continue

    # Step 4 — send completion email
    send_mail(
        subject="Your Letterboxd list has been imported!",
        message=(
            f"Hi {user.username},\n\n"
            f"Your list '{film_list.title}' has been imported to Kinorg.\n"
            f"{imported_count} films imported successfully"
            + (f", {failed_count} could not be matched." if failed_count else ".") +
            f"\n\nView it here: https://kinorg.com/lists/{film_list.sqid}/"
        ),
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
    )