"""
Crawler implementation.
"""
# pylint: disable=too-many-arguments, too-many-instance-attributes, unused-import, undefined-variable
import datetime
import json
import pathlib
import re
from random import randrange
from time import sleep
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH


class IncorrectSeedURLError(Exception):
    """
    The seed url does not match standard pattern.
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of range from 1 to 150.
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Total number of articles to parse is not integer.
    """


class IncorrectHeadersError(Exception):
    """
    The headers are not in a form of dictionary.
    """


class IncorrectEncodingError(Exception):
    """
    The encoding is not a string.
    """


class IncorrectTimeoutError(Exception):
    """
    The timeout value must be a positive integer less than 60.
    """


class IncorrectVerifyError(Exception):
    """
    Verify certificate value must either be True or False.
    """


class Config:
    """
    Class for unpacking and validating configurations.
    """

    def __init__(self, path_to_config: pathlib.Path) -> None:
        """
        Initialize an instance of the Config class.

        Args:
            path_to_config (pathlib.Path): Path to configuration.
        """
        self.path_to_config = path_to_config
        self.config = self._extract_config_content()
        self._validate_config_content()

        self._seed_urls = self.config.seed_urls
        self._num_articles = self.config.total_articles
        self._headers = self.config.headers
        self._encoding = self.config.encoding
        self._timeout = self.config.timeout
        self._should_verify_certificate = self.config.should_verify_certificate
        self._headless_mode = self.config.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Get config values.

        Returns:
            ConfigDTO: Config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config = json.load(file)
        return ConfigDTO(**config)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters are not corrupt.
        """
        if not isinstance(self.config.seed_urls, list):
            raise IncorrectSeedURLError("Seed URL does not match standard pattern 'https?://(www.)?'")

        for seed_url in self.config.seed_urls:
            if not re.match(r"https?://(www.)?", seed_url):
                raise IncorrectSeedURLError("Seed URL does not match standard pattern 'https?://(www.)?'")

        if not isinstance(self.config.total_articles, int) or self.config.total_articles <= 0:
            raise IncorrectNumberOfArticlesError("Total number of articles to parse is not an integer")

        if not 0 < self.config.total_articles < 150:
            raise NumberOfArticlesOutOfRangeError("Total number of articles is out of range from 1 to 150")

        if not isinstance(self.config.headers, dict):
            raise IncorrectHeadersError("Headers are not in the form of a dictionary")

        if not isinstance(self.config.encoding, str):
            raise IncorrectEncodingError("Encoding must be specified as a string")

        if not isinstance(self.config.timeout, int) or not 0 <= self.config.timeout < 60:
            raise IncorrectTimeoutError("Timeout value must be a positive integer less than 60")

        if (not isinstance(self.config.should_verify_certificate, bool) or
                not isinstance(self.config.headless_mode, bool)):
            raise IncorrectVerifyError("Verify certificate value must be either True or False")

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls.

        Returns:
            list[str]: Seed urls
        """
        return self._seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape.

        Returns:
            int: Total number of articles to scrape
        """
        return self._num_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting.

        Returns:
            dict[str, str]: Headers
        """
        return self._headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing.

        Returns:
            str: Encoding
        """
        return self._encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response.

        Returns:
            int: Number of seconds to wait for response
        """
        return self._timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate.

        Returns:
            bool: Whether to verify certificate or not
        """
        return self._should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode.

        Returns:
            bool: Whether to use headless mode or not
        """
        return self._headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Deliver a response from a request with given configuration.

    Args:
        url (str): Site url
        config (Config): Configuration

    Returns:
        requests.models.Response: A response from a request
    """
    sleep(randrange(5))
    return requests.get(
        url=url,
        timeout=config.get_timeout(),
        headers=config.get_headers(),
        verify=config.get_verify_certificate())


class Crawler:
    """
    Crawler implementation.
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initialize an instance of the Crawler class.

        Args:
            config (Config): Configuration
        """
        self.config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.BeautifulSoup): BeautifulSoup instance

        Returns:
            str: Url from HTML
        """
        links = article_bs.find_all('a', class_='listing-preview__content')
        url = ''
        for link in links:
            url = link['href']
        return url

    def find_articles(self) -> None:
        """
        Find articles.
        """
        for url in self.get_search_urls():
            response = make_request(url, self.config)
            if not response.ok:
                continue

            article_bs = BeautifulSoup(response.text, "lxml")
            for i in range(30):
                extracted_url = self._extract_url(article_bs)
                if extracted_url:
                    self.urls.append(extracted_url)

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self.config.get_seed_urls()


# 10
# 4, 6, 8, 10


class HTMLParser:
    """
    HTMLParser implementation.
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initialize an instance of the HTMLParser class.

        Args:
            full_url (str): Site url
            article_id (int): Article id
            config (Config): Configuration
        """
        self.full_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        text = article_soup.find_all(itemprop="articleBody")
        description = article_soup.find(itemprop="description")
        article = ''
        if description:
            article += description.text
        for paragraph in text:
            article += paragraph.text
        self.article.text = article

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        author = article_soup.find("li", itemprop="author")
        if author:
            self.article.author = [author.text.strip()]
        else:
            self.article.author = ["NOT FOUND"]
        self.article.title = article_soup.find(itemprop="headline").text.strip()

        article_date = article_soup.find('time', class_='meta__text').text
        formatted_date = ''.join(article_date.split(' в '))
        self.article.date = self.unify_date_format(formatted_date)

        tags = article_soup.find_all('a', class_='article__tag-item')
        for tag in tags:
            self.article.topics.append(tag.text)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
         Unify date format.

         Args:
             date_str (str): Date in text format

         Returns:
             datetime.datetime: Datetime object
         """
        return datetime.datetime.strptime(date_str, "%d.%m.%Y %H:%M")

    def parse(self) -> Union[Article, bool, list]:
        """
        Parse each article.

        Returns:
            Union[Article, bool, list]: Article instance
        """
        response = make_request(self.full_url, self.config)
        if response.ok:
            article_bs = BeautifulSoup(response.text, 'lxml')
            self._fill_article_with_text(article_bs)
            self._fill_article_with_meta_information(article_bs)

        return self.article


def prepare_environment(base_path: Union[pathlib.Path, str]) -> None:
    """
    Create ASSETS_PATH folder if no created and remove existing folder.

    Args:
        base_path (Union[pathlib.Path, str]): Path where articles stores
    """
    if not base_path.exists():
        base_path.mkdir(parents=True)
    base_path.rmdir()
    base_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module.
    """
    config = Config(CRAWLER_CONFIG_PATH)
    crawler = Crawler(config)
    crawler.find_articles()
    prepare_environment(ASSETS_PATH)

    for index, url in enumerate(crawler.get_search_urls()):
        parser = HTMLParser(url, index, config)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)


if __name__ == "__main__":
    main()
