import datetime
import random

import requests
from requests import Response
from requests.exceptions import HTTPError
from retry import retry

from src.constants import PROXY_REPO_URL
from src.logger import logger


class ProxyRotator:
    def __init__(self, reload_sec: int):
        self._last_updated = datetime.datetime.now(datetime.UTC)
        self._reload_sec = reload_sec
        self.proxy_url = PROXY_REPO_URL
        self.proxies = self.load_proxies()

    @logger.catch(reraise=True)
    @retry(exceptions=HTTPError, tries=5, delay=2, logger=logger)
    def load_proxies(self):
        response = requests.get(self.proxy_url)
        cleaned_proxies = self._clean_response(response)
        self._last_updated = datetime.datetime.now(datetime.UTC)
        logger.info(
            f"Loaded {len(cleaned_proxies)} proxies from Github at {self._last_updated}"
        )
        return cleaned_proxies

    def _is_proxies_expired(self):
        now = datetime.datetime.now(datetime.UTC)
        return now - self._last_updated >= datetime.timedelta(seconds=self._reload_sec)

    def _clean_response(self, response: Response) -> list[str]:
        # Split the line by ':' and take the first two parts (IP and port)
        lines = response.text.splitlines()
        return [":".join(line.split(":")[:2]) for line in lines]

    def get_random_proxy(self):
        if self._is_proxies_expired():
            logger.info(
                f"Proxies expired (last loaded at {self._last_updated}), reloading..."
            )
            self.proxies = self.load_proxies()
        ip_port = random.choice(self.proxies)
        return f"https://{ip_port}"
