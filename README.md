# MoveVideo

Python application for video management, integration with qBittorrent and Stash, duplicate detection, and RSS feed generation.

## Overview

**MoveVideo** is a suite of Python scripts designed to automate video library management through three main components:

### MoveVideo.py
Moves video files from a source directory to a destination, organizes them by category, and cleans up empty directories. It monitors specific folders and automatically transfers completed downloads to their final locations.

### ManageStash.py
Integrates with Stash (media server) to manage video metadata, detect duplicates, and automate library maintenance. Key features include:
- Library scanning and metadata scraping from remote sources
- Duplicate detection and cleanup based on phash/oshash fingerprints
- Tag management and scene organization
- Garbage collection for corrupted or misplaced files

### ManageQBittorrent.py
Manages qBittorrent through its Web API to automate torrent operations:
- Generates reports on torrent status and categories
- Cleans up completed and moved torrents from the list
- Controls file download priorities (e.g., disabling files > 3 GB in specific categories)
- Supports dry-run mode for safe testing

The project is structured as an official Python package (`App/`) for better portability and maintainability.

## Prerequisites

### Required Software

- Python 3.12 or higher
- `pip install -r requirements.txt`

### Configuration

The project requires a configuration file `config/config.toml` with the following structure:

## Installation

1. Clone or copy the repository to your working directory
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   . venv/bin/activate  # Linux/macOS
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create the `config/config.toml` file with your setup settings
5. Verify that qBittorrent and Stash are reachable from their respective host/port

## Usage

### Main Execution

The application can be run from the project root:

```bash
python -m App.MoveVideo
```

Or directly from the `App/` folder:
```bash
python App/MoveVideo.py
```

### Available Commands

The application supports various commands through command-line arguments (see individual files for details):

- **MoveVideo**: `move_files`, `delete_small_directories`, `is_video_file`
- **ManageStash**: scan, delete_duplicates_scenes, process_files, garbage collection
- **StashCli**: matching, scraping, update operations
- **ProxiedScraper**: periodic scraping, RSS generation

### Basic Example

To start moving video files:
```bash
python -m App.MoveVideo
```

To run a full scan on Stash:
```bash
python -m App.ManageStash --scan
```

## Project Structure

```
MoveVideo/
├── README.md          # This file
├── requirements.txt   # Python dependencies
├── config/            # Configuration folder
│   └── config.toml    # qBittorrent/Stash configuration
├── App/               # Main Python package
│   ├── __init__.py    # Package initialization
│   ├── Config.py      # Configuration management and environment overrides
│   ├── Log.py         # Custom logging utility
│   ├── Types.py       # Shared dataclasses and constants
│   ├── FindBestFile.py# Duplicate file selection logic
│   ├── MoveVideo.py   # File moving and directory cleanup
│   ├── ManageQBittorent.py  # qBittorrent client
│   ├── ManageStash.py # Stash integration
│   ├── StashCli.py    # CLI for Stash operations
│   ├── ProxiedScraper.py  # Web scraper + RSS server
│   └── Test.py        # Test/execution script
├── tests/             # Unit tests
│   └── test_findbestfile.py
└── Dockerfile         # Docker configuration (if present)
```

## Advanced Configuration

### Environment Variables

Environment variables can override values in `config.toml`:

- `QBITTORENT_USERNAME`
- `QBITTORENT_PASSWORD`
- `STASH_API_KEY`
- `STASH_HOST` (format: `http://host:port`)

### Customization

- Add new proxy scrapers in `ProxiedScraper.py`
- Modify `MATCHES_STASHBOX` constants in `App/Types.py`
- Extend file selection logic in `App/FindBestFile.py`

## Notes and Limitations

- The application has been tested with qBittorrent and Stash in a home environment
- Some features require services to be reachable from the machine running the script
- Duplicate detection relies on fingerprints (phash/oshash) present in Stash metadata
- Trash and download directories are configurable but assume absolute paths

## License

This project is open source. Please consult any license files present.