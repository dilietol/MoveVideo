import json
import os
import time

import qbittorrentapi
from qbittorrentapi import Client
import configparser
import logging

logger = logging.getLogger("QBitTorrentClient")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(name)s %(message)s")
formatter.converter = time.localtime
ch.setFormatter(formatter)
logger.addHandler(ch)


def log(msg):
    logger.info(msg)


def debug(msg):
    logger.debug(msg)


def log_end(title):
    log("********************** %s END **********************" % title)


def log_start(title):
    log("********************** %s START **********************" % title)


class QBitTorrentClient:
    conf: configparser.ConfigParser
    client: Client

    def __init__(self):
        self.initialize()

    def get_active_torrents(self):
        torrents = ()
        if self.client.is_logged_in:
            torrents = self.client.torrents_info()
        active_torrents = [torrent for torrent in torrents if torrent['state'] == 'downloading']
        return active_torrents

    def log_torrents_report(self):
        counters = {}
        torrents = ()
        if self.client.is_logged_in:
            torrents = self.client.torrents_info()
        for torrent in torrents:
            parameter = torrent.state
            if parameter in counters:
                counters[parameter] += 1
            else:
                counters[parameter] = 1
        log("counters for not valid duplicates: " + json.dumps(counters))

    def get_completed_and_moved_torrents(self):
        torrents = ()
        if self.client.is_logged_in:
            torrents = self.client.torrents_info()
        completed_torrents = [torrent for torrent in torrents if (
                (not torrent['content_path'].startswith(self.conf['Path']['Incomplete'])) and torrent[
            'content_path'].startswith(self.conf['Path']['Downloads']) and torrent['state'] in ['pausedUP',
                                                                                                'stalledUP',
                                                                                                'queuedUP',
                                                                                                'uploading',
                                                                                                'missingFiles'])]
        return completed_torrents

    def main(self):
        log_start("Main")
        self.client.auth_log_in()
        self.log_torrents_report()
        for torrent in self.get_active_torrents():
            log(f"{torrent.hash}: {torrent.name} ({torrent.state})")
        torrents = self.get_completed_and_moved_torrents()
        for torrent in torrents:
            log(f"{torrent.hash}: {torrent.name} ({torrent.state})")
        for torrent in torrents:
            self.client.torrents_delete(delete_files=False, torrent_hashes=[torrent.hash])
            log("Deleted torrent with name " + torrent.name)
        self.client.auth_log_out()

        log_end("Main")

    def parse_config(self):
        self.conf = configparser.ConfigParser()
        defaults_path = os.path.join('config', 'config.toml')
        self.conf.read(defaults_path)

    def initialize(self):
        self.parse_config()
        # Set up client
        args = {
            "host": self.conf["QBittorent_Host"]["Host"],
            "port": int(self.conf["QBittorent_Host"]["Port"]),
            "username": self.conf["QBittorent_Host"]["username"],
            "password": self.conf["QBittorent_Host"]["password"]
        }
        self.client = qbittorrentapi.Client(**args)
        try:
            self.client.auth_log_in()
            log_start("Config")
            log(f"qBittorrent: {self.client.app.version}")
            log(f"qBittorrent Web API: {self.client.app.web_api_version}")
            for k, v in self.client.app.build_info.items():
                log(f"{k}: {v}")
            log_end("Config")
            self.client.auth_log_out()
        except qbittorrentapi.LoginFailed as e:
            log(e)
        except Exception as e:
            log(e)


if __name__ == '__main__':
    qb_api = QBitTorrentClient()
    qb_api.main()
