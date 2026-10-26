import argparse
import json
import os
import toml

import qbittorrentapi
from qbittorrentapi import Client
from App.Config import apply_env_overrides
from App.Log import Logger

class QBitTorrentClient:
    client: Client
    logger: Logger

    def __init__(self):
        self.conf = None
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

    def log_torrents_report(self, torrents):
        self.logger.log_start("Torrents Report")
        if torrents is None:
            torrents = []
        self.logger.log("Torrents Number : " + str(len(torrents)))
        
        counters = {}
        category_counts = {}
        for torrent in torrents:
            parameter = torrent.state
            if parameter in counters:
                counters[parameter] += 1
            else:
                counters[parameter] = 1
            category = torrent.category if torrent.category else "Uncategorized"
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += 1
        self.logger.log("Torrents state counters: " + json.dumps(counters))
        self.logger.log("Torrents category counters: " + json.dumps(category_counts))
        self.logger.log_end("Torrents Report")



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

    def process_completed_torrents(self, dry_run=True):
        self.logger.log_start("Process Completed Torrents")
        self.logger.log("Dry run: " + str(dry_run))
        
        try:
            self.client.auth_log_in()
            
            if not self.client.is_logged_in:
                self.logger.error("Failed to log in to qbittorrent")
                raise Exception("Login failed: not authenticated")
            
            self.logger.log("Logged in to qbittorrent")
            # Single API call to fetch all torrents
            all_torrents = self.client.torrents_info()

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
                
            self.logger.log("Number of completed torrents to delete: " + str(len(completed_torrents)))
                
            for torrent in completed_torrents:
                if not dry_run:
                    try:
                        self.client.torrents_delete(delete_files=False, torrent_hashes=[torrent.hash])
                        self.logger.log("Deleted torrent with name " + torrent.name)
                    except Exception as e:
                        self.logger.error(f"Failed to delete torrent {torrent.name}: {e}")
                else:
                    self.logger.log(f"[DRY RUN] Would delete torrent: {torrent.name}")
        except Exception as e:
            self.logger.error(f"Process completed torrents failed: {e}")
        finally:
            try:
                self.client.auth_log_out()
                self.logger.log_end("Process Completed Torrents")
            except Exception as e:
                self.logger.error(f"Logout failed: {e}")

    def disable_large_files_download(self, dry_run=True):
        self.logger.log_start("Disable Large Files Download")
        self.logger.log("Dry run: " + str(dry_run))
        
        try:
            self.client.auth_log_in()
            
            if not self.client.is_logged_in:
                self.logger.error("Failed to log in to qbittorrent")
                raise Exception("Login failed: not authenticated")
            
            self.logger.log("Logged in to qbittorrent")
            # Single API call to fetch all torrents
            all_torrents = self.client.torrents_info()
            
            # Filter active torrents in category xxx
            target_category = "xxx"
            active_torrents = [torrent for torrent in all_torrents 
                              if torrent['state'] in ['downloading', 'queuedDL', 'stalledDL'] 
                              and torrent['category'] == target_category]
            
            self.logger.log(f"Active torrents in category '{target_category}': {len(active_torrents)}")
            
            size_limit = 3 * 1024 * 1024 * 1024  # 3 GB in bytes
            total_files_disabled = 0
            
            for torrent in active_torrents:
                self.logger.log(f"Processing torrent: {torrent.name} (hash: {torrent.hash})")
                
                # Get torrent files
                torrent_files = self.client.torrents_files(torrent_hash=torrent.hash)
                
                files_to_disable = []
                for file_info in torrent_files:
                    if file_info.size > size_limit:
                        files_to_disable.append(file_info.id)
                        self.logger.log(f"  File > 3GB: {file_info.name} ({file_info.size / (1024**3):.2f} GB)")
                
                if files_to_disable:
                    self.logger.log(f"  Found {len(files_to_disable)} files > 3GB to disable download")
                    total_files_disabled += len(files_to_disable)
                    
                    if not dry_run:
                        try:
                            # Set file priority to 0 (do not download)
                            for file_id in files_to_disable:
                                self.client.torrents_file_priority(
                                    torrent_hash=torrent.hash,
                                    file_ids=file_id,
                                    priority=0
                                )
                            self.logger.log(f"  Disabled download for {len(files_to_disable)} files")
                        except Exception as e:
                            self.logger.error(f"  Failed to disable files for torrent {torrent.name}: {e}")
                    else:
                        self.logger.log(f"  [DRY RUN] Would disable download for {len(files_to_disable)} files")
                else:
                    self.logger.log(f"  No files > 3GB found")
            
            self.logger.log(f"Total files to disable across all torrents: {total_files_disabled}")
        except Exception as e:
            self.logger.error(f"Disable large files download failed: {e}")
        finally:
            try:
                self.client.auth_log_out()
                self.logger.log_end("Disable Large Files Download")
            except Exception as e:
                self.logger.error(f"Logout failed: {e}")

    def main(self):
        parser = argparse.ArgumentParser(description='Manage qBittorrent operations')
        parser.add_argument('--report', action='store_true',
                            help='Generate report of completed torrents and delete them')
        parser.add_argument('--disable3G', action='store_true',
                            help='Disable download of video files > 3GB for active torrents in category xxx')
        parser.add_argument('--execute', action='store_true', help='Execute operations (default is dry-run)')

        args = parser.parse_args()
        dry_run = not args.execute

        if args.report:
            self.process_completed_torrents(dry_run)

        if args.disable3G:
            self.disable_large_files_download(dry_run)

    def parse_config(self):
        defaults_path = None
        try:
            defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.toml')
            with open(defaults_path, 'r') as f:
                self.conf = apply_env_overrides(toml.load(f))
        except FileNotFoundError:
            self.logger.log(f"Config file not found: {defaults_path}")
            raise
        except toml.TomlDecodeError as e:
            self.logger.log(f"Invalid TOML in config file: {e}")
            raise

    def initialize(self):
        self.logger.log_start(" Starting ManageQBittorent ")
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
            "username": self.conf["QBittorent_Host"].get("username", ""),
            "password": self.conf["QBittorent_Host"].get("password", "")
        }
        if not args["password"]:
            self.logger.log("qBittorrent password is empty: set the QBITTORENT_PASSWORD environment variable")
        
        # Validate required config sections exist
        required_sections = ["QBittorent_Host", "Path"]
        for section in required_sections:
            if section not in self.conf:
                self.logger.error(f"Required configuration section {section} not found")
                raise KeyError(f"Missing required configuration section: {section}")
        
        self.client = qbittorrentapi.Client(**args)
        try:
            self.client.auth_log_in()
            self.logger.log_start(" qBittorrent server configuration ")
            self.logger.log(f"qBittorrent: {self.client.app.version}")
            self.logger.log(f"qBittorrent Web API: {self.client.app.web_api_version}")
            for k, v in self.client.app.build_info.items():
                self.logger.log(f"{k}: {v}")
            self.logger.log_end(" qBittorrent server configuration ")
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
