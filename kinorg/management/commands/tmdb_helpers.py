"""
Shared TMDB utilities for import/audit management commands.

search_tmdb(title, year) tries a movie search first. If nothing is found it
falls back to a TV search and only accepts results whose TMDB type is
'Miniseries' — keeping TV additions narrow and intentional.

Returns: (tmdb_id, media_type, prefetched_detail)
  - Movie found:       (id, 'movie', None)          — detail not yet fetched
  - Miniseries found:  (id, 'tv',    detail_dict)   — detail already fetched
  - Nothing found:     (None, None,  None)
"""
import os
import time

import requests

TMDB_SEARCH_MOVIE = "https://api.themoviedb.org/3/search/movie"
TMDB_SEARCH_TV    = "https://api.themoviedb.org/3/search/tv"
TMDB_MOVIE_DETAIL = "https://api.themoviedb.org/3/movie/{}"
TMDB_TV_DETAIL    = "https://api.themoviedb.org/3/tv/{}"


def tmdb_headers():
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {os.environ.get('TMDB_KEY', '')}",
    }


def search_tmdb(title, year):
    # --- movie search ---
    r = requests.get(TMDB_SEARCH_MOVIE, headers=tmdb_headers(), params={
        'query': title,
        'year': int(year),
        'language': 'en-US',
    }, timeout=10)
    results = r.json().get('results', [])
    if results:
        return results[0]['id'], 'movie', None

    # --- TV fallback ---
    time.sleep(0.25)
    r = requests.get(TMDB_SEARCH_TV, headers=tmdb_headers(), params={
        'query': title,
        'first_air_date_year': int(year),
        'language': 'en-US',
    }, timeout=10)
    tv_results = r.json().get('results', [])
    if not tv_results:
        return None, None, None

    # Fetch TV detail to check type — only accept Miniseries
    time.sleep(0.25)
    tv_id = tv_results[0]['id']
    detail = fetch_tmdb_detail(tv_id, 'tv')
    if detail and detail.get('type') == 'Miniseries':
        return tv_id, 'tv', detail

    return None, None, None


def fetch_tmdb_detail(tmdb_id, media_type='movie'):
    url = TMDB_TV_DETAIL if media_type == 'tv' else TMDB_MOVIE_DETAIL
    r = requests.get(
        url.format(tmdb_id) + "?append_to_response=credits,keywords&language=en-US",
        headers=tmdb_headers(), timeout=10,
    )
    return r.json() if r.status_code == 200 else None


def build_defaults(data, media_type='movie'):
    crew = data.get('credits', {}).get('crew', [])
    cast = data.get('credits', {}).get('cast', [])
    countries = [c['iso_3166_1'] for c in data.get('production_countries', [])]

    # Keywords structure differs between movie and TV endpoints
    kw_blob = data.get('keywords', {})
    keywords = kw_blob.get('keywords') or kw_blob.get('results') or []

    if media_type == 'tv':
        title        = data.get('name', '')
        release_date = data.get('first_air_date') or None
        runtimes     = data.get('episode_run_time', [])
        runtime      = runtimes[0] if runtimes else None
    else:
        title        = data.get('title', '')
        release_date = data.get('release_date') or None
        runtime      = data.get('runtime')

    return {
        'title':                title,
        'release_date':         release_date,
        'poster_path':          data.get('poster_path', '') or '',
        'backdrop_path':        data.get('backdrop_path', '') or '',
        'overview':             data.get('overview', ''),
        'genres':               [g['name'] for g in data.get('genres', [])],
        'cast':                 [a['name'] for a in cast[:5]],
        'crew':                 [{'name': c['name'], 'job': c['job']} for c in crew
                                 if c['job'] in ('Director', 'Screenplay', 'Writer')],
        'keywords':             [k['name'] for k in keywords],
        'runtime':              runtime,
        'production_companies': [c['name'] for c in data.get('production_companies', [])[:3]],
        'production_countries': countries,
        'primary_country':      countries[0] if countries else '',
        'media_type':           media_type,
    }
