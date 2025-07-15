import os
import requests
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='logs/cache.log',
    format='%(asctime)s - %(message)s',
    encoding='utf-8', 
    level=logging.INFO
    )

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
    config_response = requests.get(config_url, headers=headers)
    config_data = config_response.json()

    # cache for 24 hours
    images_config = config_data["images"]
    cache.set('tmdb_config', config_data["images"], timeout=86400)
    logger.info('Image config fetched and cached')

    return {
        'config_data': images_config
        }