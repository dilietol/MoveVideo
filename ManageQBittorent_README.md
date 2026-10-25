# ManageQBittorrent - Documentation

## Overview

`ManageQBittorrent` is a Python client for managing qBittorrent through its Web API. The program connects to a remote qBittorrent instance, monitors torrents, and automatically cleans up completed and moved torrents.

## Main Features

### 1. Connection to qBittorrent
- Automatic connection to a remote qBittorrent instance via API
- Authentication with username and password
- Verification of API and client version
- Handling of connection and authentication errors

### 2. Torrent Monitoring
- **Active Torrents**: Retrieves and logs all torrents in download state (`downloading`)
- **Full Report**: Generates a report with torrent count for each state (pausedUP, stalledUP, queuedUP, uploading, stoppedUP, missingFiles, etc.)

### 3. Automatic Cleanup
The program identifies and automatically removes completed torrents that meet these criteria:
- File path **DOES NOT** start with the `Incomplete` folder
- File path **STARTS** with the `Downloads` folder
- Torrent state is one of the following:
  - `pausedUP` - Paused after upload
  - `stalledUP` - Upload stalled
  - `queuedUP` - Queued for upload
  - `uploading` - Uploading
  - `stoppedUP` - Stopped after upload
  - `missingFiles` - Missing files

Torrents are removed from the qBittorrent list but **files are NOT deleted** from disk.

## Configuration

The program requires a `App/config/config.toml` file with the following sections:

### [QBittorent_Host]
qBittorrent connection configuration:
- `Host`: IP address or hostname of the qBittorrent server
- `Port`: Port of the qBittorrent server
- `username`: Username for authentication
- `password`: Password for authentication

### [Path]
Paths for torrent filtering:
- `Incomplete`: Path of the incomplete downloads folder
- `Downloads`: Path of the completed downloads folder

### Configuration Example
```toml
[QBittorent_Host]
Host = "192.168.1.88"
Port = 8080
username = "admin"
password = "your_password"

[Path]
Incomplete = "/downloads/incomplete"
Downloads = "/downloads"
```

## Class Methods

### `__init__()`
Initializes the client, loads configuration, and establishes connection to qBittorrent.

### `get_active_torrents()`
Returns the list of torrents currently downloading.

### `log_torrents_report(torrents=None)`
Generates and logs a report with torrent count for each state.

### `get_completed_and_moved_torrents()`
Returns the list of completed and moved torrents that meet cleanup criteria.

### `main()`
Executes the main flow:
1. Performs login
2. Retrieves all torrents
3. Logs full report
4. Logs active torrents
5. Identifies completed torrents
6. Removes completed torrents from list
7. Performs logout

### `parse_config()`
Loads and validates the TOML configuration file.

### `initialize()`
Configures the qBittorrent client with parameters from configuration file and verifies connection.

## Error Handling

The program includes robust error handling:
- Connection and authentication errors
- Missing or invalid configuration file
- Errors during torrent retrieval
- Errors during torrent deletion
- All errors are logged with descriptive messages

## Usage

Run the script directly:
```bash
python ManageQBittorent.py
```

Or import and use the class in other code:
```python
from ManageQBittorent import QBitTorrentClient

qb_client = QBitTorrentClient()
qb_client.main()
```

## Requirements

- Python 3.x
- qbittorrentapi
- toml
- A qBittorrent instance with Web API enabled
