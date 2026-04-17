import os
import requests
import logging
from django.core.cache import cache
from kinorg.models import Invitation

logger = logging.getLogger(__name__)

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
