import os
import requests
import logging
from django.core.cache import cache
from kinorg.models import Invitation, WatchedFilm, LikedFilm, WatchlistItem, FilmList, Addition

logger = logging.getLogger(__name__)

KINORG_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours


def kinorg_cache_key(user_id):
    return f"kinorg_user_{user_id}"


def build_user_kinorg_data(user):
    """Query the DB and build the full user data dict. Called on cache miss."""
    watched_ids = list(WatchedFilm.objects.filter(user=user).values_list('film_id', flat=True))
    liked_ids = list(LikedFilm.objects.filter(user=user).values_list('tmdb_id', flat=True))
    watchlist_ids = list(WatchlistItem.objects.filter(user=user).values_list('film_id', flat=True))

    my_lists = list(FilmList.objects.filter(owner=user, archived=False).order_by('-id'))
    guest_lists = list(FilmList.objects.filter(guests=user, archived=False).order_by('-id'))

    lists_data = []
    for lst in my_lists + guest_lists:
        film_ids = list(Addition.objects.filter(film_list=lst).values_list('film_id', flat=True))
        lists_data.append({
            'id': lst.id,
            'sqid': lst.sqid,
            'title': lst.title,
            'film_ids': film_ids,
            'is_owner': lst.owner_id == user.id,
        })

    return {
        'watched_ids': watched_ids,
        'liked_ids': liked_ids,
        'watchlist_ids': watchlist_ids,
        'lists': lists_data,
    }


def get_user_kinorg_data(request):
    """Context processor: attach cached user data to every template context.
    Skips JSON/AJAX requests to avoid unnecessary cache population."""
    if not request.user.is_authenticated:
        return {'kinorg_data': None}
    if request.headers.get('Accept') == 'application/json':
        return {'kinorg_data': None}

    key = kinorg_cache_key(request.user.id)
    data = cache.get(key)
    if data is None:
        try:
            data = build_user_kinorg_data(request.user)
            cache.set(key, data, KINORG_CACHE_TIMEOUT)
        except Exception:
            logger.exception('Failed to build kinorg user data')
            return {'kinorg_data': None}

    return {'kinorg_data': data}


def get_pending_invitations(request):
    if not request.user.is_authenticated:
        return {'pending_invitation_count': 0}
    count = Invitation.objects.filter(to_user=request.user, accepted=False, declined=False).count()
    return {'pending_invitation_count': count}


TMDB_FALLBACK_CONFIG = {
    'secure_base_url': 'https://image.tmdb.org/t/p/',
}


def get_image_config(request):

    # Check for data
    cached_images_config = cache.get('tmdb_config')
    if cached_images_config:
        logger.info('Image config retrieved from cache')
        return {'config_data': cached_images_config}

    # if no data, fetch
    logger.info('config not in cache, fetching from API')
    api_key = os.environ.get('TMDB_KEY')
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    config_url = "https://api.themoviedb.org/3/configuration"
    try:
        config_response = requests.get(config_url, headers=headers, timeout=5)
        config_data = config_response.json()
        images_config = config_data["images"]
        cache.set('tmdb_config', images_config, timeout=86400)
        logger.info('Image config fetched and cached')
        return {'config_data': images_config}
    except Exception as e:
        logger.warning(f'Failed to fetch TMDB image config, using fallback: {e}')
        return {'config_data': TMDB_FALLBACK_CONFIG}
