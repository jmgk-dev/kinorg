import os

import requests

def get_image_config(request):

    api_key = os.environ.get('TMDB_KEY')

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    config_url = "https://api.themoviedb.org/3/configuration"
    config_response = requests.get(config_url, headers=headers)
    config_data = config_response.json()

    return {
        'config_data': config_data["images"],
        }