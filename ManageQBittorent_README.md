# ManageQBittorrent - Documentation

## Overview

`ManageQBittorrent` is a Python client for managing qBittorrent through its Web API. The program connects to a remote qBittorrent instance, monitors torrents, and provides various operations for torrent management including cleanup and file download control.

## Main Features

### 1. Connection to qBittorrent
- Automatic connection to a remote qBittorrent instance via API
- Authentication with username and password
- Verification of API and client version
- Handling of connection and authentication errors

### 2. Torrent Monitoring
- **Active Torrents**: Retrieves and logs all torrents in download state (`downloading`)
- **Full Report**: Generates a report with torrent count for each state (pausedUP, stalledUP, queuedUP, uploading, stoppedUP, missingFiles, etc.)

### 3. Completed Torrent Cleanup
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

### 4. Large Files Download Control
The program can disable download of files larger than 3 GB for active torrents in specific categories:
- Filters active torrents (downloading, queuedDL, stalledDL) in category "xxx"
- Identifies files > 3 GB within each torrent
- Sets file priority to 0 (do not download) for large files
- Supports dry-run mode for testing

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

### `process_completed_torrents(dry_run=True)`
Processes completed torrents:
- Generates a full report of all torrents
- Logs active torrents
- Identifies completed torrents based on path and state
- Removes completed torrents from qBittorrent list (files not deleted)
- Supports dry-run mode for testing

### `disable_large_files_download(dry_run=True)`
Disables download of files larger than 3 GB for active torrents in category "xxx":
- Filters active torrents (downloading, queuedDL, stalledDL) in category "xxx"
- Identifies files > 3 GB within each torrent
- Sets file priority to 0 (do not download) for large files
- Supports dry-run mode for testing

### `main()`
Parses command-line arguments and executes the requested operation:
- `--report`: Generate report and clean completed torrents
- `--disable3G`: Disable download of files > 3 GB in category xxx
- `--execute`: Execute operations (default is dry-run)

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

### Command Line Interface

The script supports command-line arguments for different operations:

**Generate report and clean completed torrents (dry-run):**
```bash
python ManageQBittorent.py --report
```

**Generate report and clean completed torrents (execute):**
```bash
python ManageQBittorent.py --report --execute
```

**Disable download of files > 3 GB in category xxx (dry-run):**
```bash
python ManageQBittorent.py --disable3G
```

**Disable download of files > 3 GB in category xxx (execute):**
```bash
python ManageQBittorent.py --disable3G --execute
```

**Show help:**
```bash
python ManageQBittorent.py --help
```

### Docker Aliases

When running in the Docker container, the following aliases are available:
- `move` - Move videos and clean completed torrents
- `disable3g` - Disable download of files > 3GB in xxx category

### Programmatic Usage

Import and use the class in other code:
```python
from ManageQBittorent import QBitTorrentClient

qb_client = QBitTorrentClient()
qb_client.process_completed_torrents(dry_run=True)
qb_client.disable_large_files_download(dry_run=True)
```

## Requirements

- Python 3.x
- qbittorrentapi
- toml
- A qBittorrent instance with Web API enabled
