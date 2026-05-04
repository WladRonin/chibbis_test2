import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ServiceClient:
    def __init__(self, base_url="https://archive-api.open-meteo.com"):
        self.base_url = base_url
        self.retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        self.adapter = HTTPAdapter(max_retries=self.retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", self.adapter)
        self.session.mount("http://", self.adapter)

    def _request(self, method: str, endpoint: str, params: dict):
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method,
                url,
                timeout=(10, 30),
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            logging.error(f"HTTP error: {err}")
        except requests.exceptions.ConnectionError:
            logging.error("Connection error")
        except requests.exceptions.Timeout:
            logging.error("Timeout error")
        except requests.exceptions.RequestException as e:
            logging.error(f"Unexpected error: {e}")
        return None

    def get_weather_archive(self, params: dict):
        logging.info("Скачиваю данные погоды...")
        return self._request("GET", "v1/archive", params)

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
