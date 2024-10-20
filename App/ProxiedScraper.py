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


@dataclass
class Server:
    title: str
    url: str
    link_number: int
    column_magnet: int
    column_title: int
    interval: int
    port: int


class Scraper:
    def __init__(self, url: str, column_magnet_link: int = 2, column_description: int = 1):
        self.url = url
        self.column_magnet_link = column_magnet_link
        self.column_description = column_description

    def scrape(self) -> List[MagnetLink]:
        magnet_links = []
        session = requests.session()
        session.headers[
            "accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        session.headers[
            "accept-language"] = "en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7,es-ES;q=0.6,es;q=0.5,pt-BR;q=0.4,pt;q=0.3"
        session.headers[
            "user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
        print(session.headers)
        response = session.get(self.url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # FInd the root path
        table = soup.find('tbody')

        if table is not None:
            rows = table.find_all(name='tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    link = cells[self.column_magnet_link].find('a', href=re.compile(r'^magnet:'))
                    if link:
                        magnet_links.append(MagnetLink(
                            url=link['href'],
                            description=cells[self.column_description].get_text(strip=True)
                        ))
        else:
            # Handle the case where the 'tbody' element is not found
            print("Error: Could not find 'tbody' element in the HTML")
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
    def __init__(self, title: str, url: str, column_magnet_link: int, column_title: int, link_number=1, port=55101):
        self.title = title
        self.port = port
        urls = [f"{url}{i}" for i in range(1, link_number + 1)]
        self.scrapers = [Scraper(url, column_magnet_link=column_magnet_link, column_description=column_title) for
                         url in urls]
        self.rss_generator = RSSGenerator(
            title=self.title,
            link="",
            description=""
        )
        self.app = Flask(__name__)

    def run(self, interval: int = 30):
        self.update_feed()
        schedule.every(interval).minutes.do(self.update_feed)

        @self.app.route('/')
        def serve_rss():
            return self.rss_generator.get_feed(), 200, {'Content-Type': 'application/rss+xml'}

        self.app.run(host='0.0.0.0', port=self.port)

    def update_feed(self):
        all_links = []
        for scraper in self.scrapers:
            all_links.extend(scraper.scrape())

        self.rss_generator = RSSGenerator(
            title=self.title,
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


def initialize() -> Server:
    config = parse_config()
    server_config = config["ProxiedScaper"]
    server = Server(
        title=server_config["Title"],
        url=server_config["Url"], interval=int(server_config["Interval"]),
        column_magnet=int(server_config["Column_magnet"]),
        column_title=int(server_config["Column_title"]),
        link_number=int(server_config["Link_number"]),
        port=int(server_config["Port"]))
    return server


if __name__ == '__main__':
    server = initialize()
    app = App(server.title, server.url, server.column_magnet, server.column_title, server.link_number, server.port)
    app.run(interval=server.interval)
