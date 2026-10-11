import json
import os

import qbittorrentapi
from qbittorrentapi import Client
import configparser
from Log import Logger

class QBitTorrentClient:
    conf: configparser.ConfigParser
    client: Client

    def __init__(self):
        self.initialize()
        self.logger = Logger("QBitTorrentClient")

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
        self.logger.log("counters for not valid duplicates: " + json.dumps(counters))

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
                                                                                                'stoppedUP',
                                                                                                'missingFiles'])]
        return completed_torrents

    def main(self):
        self.logger.log_start("Main")
        self.client.auth_log_in()
        self.log_torrents_report()
        for torrent in self.get_active_torrents():
            self.logger.log(f"{torrent.hash}: {torrent.name} ({torrent.state})")
        torrents = self.get_completed_and_moved_torrents()
        for torrent in torrents:
            self.logger.log(f"{torrent.hash}: {torrent.name} ({torrent.state})")
        for torrent in torrents:
            self.client.torrents_delete(delete_files=False, torrent_hashes=[torrent.hash])
            self.logger.log("Deleted torrent with name " + torrent.name)
        self.client.auth_log_out()

        self.logger.log_end("Main")

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
            self.logger.log_start("Config")
            self.logger.log(f"qBittorrent: {self.client.app.version}")
            self.logger.log(f"qBittorrent Web API: {self.client.app.web_api_version}")
            for k, v in self.client.app.build_info.items():
                self.logger.log(f"{k}: {v}")
            self.logger.log_end("Config")
            self.client.auth_log_out()
        except qbittorrentapi.LoginFailed as e:
            self.logger.log(e)
        except Exception as e:
            self.logger.log(e)


if __name__ == '__main__':
    qb_api = QBitTorrentClient()
    qb_api.main()
