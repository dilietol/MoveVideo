import json
import os
import toml

import qbittorrentapi
from qbittorrentapi import Client
from Log import Logger

class QBitTorrentClient:
    client: Client
    logger: Logger

    def __init__(self):
        self.conf = None
        self.defaults_path = None
        self.logger = Logger("QBitTorrentClient")
        self.initialize()

    def get_active_torrents(self):
        torrents = []
        try:
            if self.client.is_logged_in:
                torrents = self.client.torrents_info()
            active_torrents = [torrent for torrent in torrents if torrent['state'] == 'downloading']
            return active_torrents
        except Exception as e:
            self.logger.error(f"Error fetching active torrents: {e}")
            return []  # Return empty list on error instead of crashing

    def log_torrents_report(self, torrents=None):
        if torrents is None:
            torrents = []
            if self.client.is_logged_in:
                torrents = self.client.torrents_info()
        
        counters = {}
        for torrent in torrents:
            parameter = torrent.state
            if parameter in counters:
                counters[parameter] += 1
            else:
                counters[parameter] = 1
        self.logger.log("counters for not valid duplicates: " + json.dumps(counters))

    def get_completed_and_moved_torrents(self):
        torrents = []
        try:
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
        except Exception as e:
            self.logger.error(f"Error fetching completed torrents: {e}")
            return []  # Return empty list on error instead of crashing

    def main(self):
        self.logger.log_start("Main")
        try:
            self.client.auth_log_in()
            # Single API call to fetch all torrents
            all_torrents = self.client.torrents_info() if self.client.is_logged_in else []
            
            self.log_torrents_report(all_torrents)
            active_torrents = [torrent for torrent in all_torrents if torrent['state'] == 'downloading']
            for torrent in active_torrents:
                self.logger.log(f"{torrent.hash}: {torrent.name} ({torrent.state})")
            
            completed_torrents = [torrent for torrent in all_torrents if (
                    (not torrent['content_path'].startswith(self.conf['Path']['Incomplete'])) and torrent[
                'content_path'].startswith(self.conf['Path']['Downloads']) and torrent['state'] in ['pausedUP',
                                                                                                    'stalledUP',
                                                                                                    'queuedUP',
                                                                                                    'uploading',
                                                                                                    'stoppedUP',
                                                                                                    'missingFiles'])]
            for torrent in completed_torrents:
                self.logger.log(f"{torrent.hash}: {torrent.name} ({torrent.state})")
                
            for torrent in completed_torrents:
                try:
                    self.client.torrents_delete(delete_files=False, torrent_hashes=[torrent.hash])
                    self.logger.log("Deleted torrent with name " + torrent.name)
                except Exception as e:
                    self.logger.error(f"Failed to delete torrent {torrent.name}: {e}")
        except Exception as e:
            self.logger.error(f"Main execution failed: {e}")
        finally:
            try:
                self.client.auth_log_out()
            except Exception as e:
                self.logger.error(f"Logout failed: {e}")

    def parse_config(self):
        try:
            self.defaults_path = os.path.join('config', 'config.toml')
            with open(self.defaults_path, 'r') as f:
                self.conf = toml.load(f)
        except FileNotFoundError:
            self.logger.log(f"Config file not found: {self.defaults_path}")
            raise
        except toml.TomlDecodeError as e:
            self.logger.log(f"Invalid TOML in config file: {e}")
            raise

    def initialize(self):
        self.parse_config()
        # Set up client with proper validation
        try:
            port = int(self.conf["QBittorent_Host"]["Port"])
        except (KeyError, ValueError) as e:
            self.logger.error(f"Invalid port configuration: {e}")
            raise
        
        args = {
            "host": self.conf["QBittorent_Host"]["Host"],
            "port": port,
            "username": self.conf["QBittorent_Host"]["username"],
            "password": self.conf["QBittorent_Host"]["password"]
        }
        
        # Validate required config sections exist
        required_sections = ["QBittorent_Host", "Path"]
        for section in required_sections:
            if section not in self.conf:
                self.logger.error(f"Required configuration section {section} not found")
                raise KeyError(f"Missing required configuration section: {section}")
        
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
            self.logger.error(f"Login failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error occurred: {e}")
            raise


if __name__ == '__main__':
    qb_api = QBitTorrentClient()
    qb_api.main()
