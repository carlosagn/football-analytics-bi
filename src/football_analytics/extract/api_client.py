import requests

from football_analytics.config.settings import API_KEY, BASE_URL


class ApiFootballClient:
    def __init__(self):
        self.headers = {
            "x-apisports-key": API_KEY
        }

    def get(self, endpoint, params=None):
        url = f"{BASE_URL}/{endpoint}"

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.json()