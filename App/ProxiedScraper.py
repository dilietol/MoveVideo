import configparser
import os

import requests
from bs4 import BeautifulSoup
import feedgenerator
from flask import Flask
import schedule
import re
from dataclasses import dataclass
from typing import List


@dataclass
class MagnetLink:
    url: str
    description: str


class Scraper:
    def __init__(self, url: str, column_magnet_link: int = 2, column_description: int = 1):
        self.url = url
        self.column_magnet_link = column_magnet_link
        self.column_description = column_description

    def scrape(self) -> List[MagnetLink]:
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # FInd the root path
        table = soup.find('tbody')

        magnet_links = []
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                link = cells[self.column_magnet_link].find('a', href=re.compile(r'^magnet:'))
                if link:
                    magnet_links.append(MagnetLink(
                        url=link['href'],
                        description=cells[self.column_description].get_text(strip=True)
                    ))

        return magnet_links


class RSSGenerator:
    def __init__(self, title: str, link: str, description: str):
        self.feed = feedgenerator.Rss201rev2Feed(
            title=title,
            link=link,
            description=description
        )

    def add_item(self, title: str, link: str, description: str):
        self.feed.add_item(
            title=title,
            link=link,
            description=description
        )

    def get_feed(self) -> str:
        return self.feed.writeString('utf-8')


class App:
    def __init__(self, url: str, column_magnet_link: int, column_title: int, link_number=1):

        urls = [f"{url}{i}" for i in range(1, link_number + 1)]
        self.scrapers = [Scraper(url, column_magnet_link=column_magnet_link, column_description=column_title) for
                         url in urls]
        self.rss_generator = RSSGenerator(
            title="Title",
            link="",
            description="Description"
        )
        self.app = Flask(__name__)

    def run(self, interval: int = 30):
        self.update_feed()
        schedule.every(interval).minutes.do(self.update_feed)

        @self.app.route('/')
        def serve_rss():
            return self.rss_generator.get_feed(), 200, {'Content-Type': 'application/rss+xml'}

        self.app.run(host='0.0.0.0', port=55101)

    def update_feed(self):
        all_links = []
        for scraper in self.scrapers:
            all_links.extend(scraper.scrape())

        self.rss_generator = RSSGenerator(
            title="Title",
            link="",
            description=""
        )

        for link in all_links:
            self.rss_generator.add_item(
                title=link.description,
                link=link.url,
                description=link.description
            )


def parse_config():
    conf = configparser.ConfigParser()
    defaults_path = os.path.join('config', 'config.toml')
    conf.read(defaults_path)
    return conf


def initialize() -> (list[str], str, int, int, int, int):
    config = parse_config()
    return (config["ProxiedScaper"]["Url"], int(config["ProxiedScaper"]["Interval"]),
            int(config["ProxiedScaper"]["Column_magnet"]), int(config["ProxiedScaper"]["Column_title"]),
            int(config["ProxiedScaper"]["Link_number"]))


if __name__ == '__main__':
    url, interval, column_magnet, column_title, link_number = initialize()
    app = App(url, column_magnet, column_title, link_number)
    app.run(interval=interval)
