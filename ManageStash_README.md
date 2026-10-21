# ManageStash Documentation

## Overview

`ManageStash` is a Python program that automates various maintenance and organization operations for Stash, a self-hosted porn organizer. It provides functionality for managing duplicates, matching scenes with external databases, updating metadata, and performing cleanup operations.

## Main Functionalities

### 1. Duplicate Management

#### Delete Duplicate Scenes
- **Method**: `delete_duplicates_scenes()`
- **Description**: Identifies and deletes duplicate scenes based on phash (perceptual hash) distance
- **Distance Levels**:
  - `EXACT`: Identical files
  - `HIGH`: Very similar files
  - `MEDIUM`: Moderately similar files
  - `LOW`: Loosely similar files
- **Features**:
  - Compares scenes using phash fingerprints
  - Determines which file to keep based on quality metrics
  - Supports dry-run mode for testing
  - Logs statistics on comparisons, file sizes, and deletion counts

#### Delete Duplicate Files
- **Method**: `delete_duplicates_files()`
- **Description**: Removes duplicate files within scenes while keeping the best version as primary
- **Features**:
  - Identifies scenes with multiple files
  - Sets the best file as primary
  - Deletes redundant files
  - Reports on space saved

### 2. Scene Matching

#### Process Matches
- **Method**: `process_matches()`
- **Description**: Searches for scene matches across multiple stashbox databases in parallel
- **Supported Stashboxes**:
  - stashdb.org (tag: MATCH_STASHDB)
  - ThePornDB (tag: MATCH_PORNDB)
  - FansDB (tag: MATCH_FANSDB)
  - PMV Stash (tag: MATCH_PMV)
- **Features**:
  - Parallel processing for faster matching
  - Tags scenes with match results
  - Marks unmatched scenes as MATCH_DONE
  - Configurable maximum number of scenes to process

#### Find Scene Matches
- **Method**: `find_scene_matches()`
- **Description**: Queries stashbox APIs to find matching scenes
- **Features**:
  - Concurrent API calls to multiple stashboxes
  - Retry logic for failed requests
  - Detailed logging of match results

### 3. Scene Updates

#### Update Scene All
- **Method**: `process_update_scene_all()`
- **Description**: Scrapes and updates all scenes marked with match tags
- **Features**:
  - Processes scenes from all stashboxes
  - Creates missing performers and studios
  - Updates scene metadata (title, date, performers, studio, URLs, cover)
  - Marks scenes as organized after successful update

#### Update Scene Path
- **Method**: `process_update_scene_path()`
- **Description**: Updates scenes within a specific directory path
- **Features**:
  - Path-specific processing
  - Same metadata update capabilities as update_all
  - Useful for targeted updates

#### Update Scene
- **Method**: `update_scene()`
- **Description**: Updates individual scene metadata
- **Metadata Updated**:
  - Title
  - Code
  - Details
  - Director
  - URLs
  - Date
  - Studio ID
  - Performer IDs
  - Cover image
  - Stash IDs
  - Organized status

### 4. Tag Management

#### Update Tags
- **Method**: `update_tags()`
- **Description**: Adds tags to scenes
- **Features**:
  - Batch processing
  - Interval logging for progress tracking
  - Retry logic for failed updates

#### Remove Tags
- **Method**: `remove_tags()`
- **Description**: Removes specified tags from scenes
- **Features**:
  - Batch tag removal
  - Combined with update_tags for persistence

#### Remove Matches
- **Method**: `remove_matches()`
- **Description**: Removes match-related tags from organized scenes
- **Tags Removed**:
  - MATCH_STASHDB
  - MATCH_PORNDB
  - MATCH_FANSDB
  - MATCH_PMV
  - MATCH_FALSE
  - MATCH_DONE
  - MATCH_UNKNOWN

#### Remove False Matches
- **Method**: `remove_false_matches()`
- **Description**: Cleans up false positive matches while preserving valid matches
- **Features**:
  - Filters scenes with only false positives and unknown tags
  - Removes stashbox match tags
  - Keeps MATCH_DONE for clean scenes

#### Reset Scene Path
- **Method**: `process_reset_scene_path()`
- **Description**: Removes MATCH_DONE tag from scenes in a specific path
- **Use Case**: Re-process scenes that were previously marked as done

### 5. Entity Creation

#### Create Performer
- **Method**: `create_performer()`
- **Description**: Creates performer entities with comprehensive metadata
- **Metadata Includes**:
  - Name and disambiguation
  - URLs
  - Gender
  - Birthdate
  - Ethnicity
  - Country
  - Eye color
  - Height
  - Measurements
  - Tattoos and piercings
  - Aliases
  - Images
  - Details
  - Stash IDs

#### Create Studio
- **Method**: `create_studio()`
- **Description**: Creates studio entities
- **Metadata Includes**:
  - Name
  - URLs
  - Parent studio
  - Image
  - Stash IDs

### 6. Cleanup and Maintenance

#### Process Corrupted
- **Method**: `process_corrupted()`
- **Description**: Identifies and deletes scenes without phash (corrupted files)
- **Detection**: Scenes with null phash_distance

#### Process Trash
- **Method**: `process_trash()`
- **Description**: Deletes scenes located in the Trash directory
- **Configurable**: Trash path from configuration file

#### Process Scan
- **Method**: `process_scan()`
- **Description**: Triggers Stash metadata scan
- **Use Case**: Rescan library for new files and metadata

#### Garbage Collection
- **Method**: Combined cleanup operations
- **Operations**:
  - Remove corrupted scenes
  - Remove trash scenes
  - Remove match tags from organized scenes
  - Remove false positive matches

### 7. Scene Search and Filtering

#### Find Scenes by Tags
- **Method**: `find_scenes_by_tags()`
- **Description**: Searches scenes using tag filters
- **Filters**:
  - Tags to include
  - Tags to exclude
  - Organized status
  - Modifier: INCLUDES_ALL

#### Find Scenes by Scene Filter
- **Method**: `find_scenes_by_scene_filter()`
- **Description**: Generic scene search with custom filters
- **Features**:
  - Pagination support
  - Configurable page size
  - Maximum scene limit
  - Sorting options

#### Find Scenes by File Count
- **Method**: `find_scenes_by_filecount()`
- **Description**: Finds scenes with specific number of files
- **Use Case**: Identify scenes with multiple files for duplicate management

#### Find Scenes by Tags and Path
- **Method**: `find_scenes_by_tags_path()`
- **Description**: Searches scenes by tags within a specific path
- **Features**:
  - Tag filtering
  - Path filtering
  - Organized status

### 8. Utility Functions

#### Get Tags
- **Method**: `get_tags()`
- **Description**: Retrieves tags from Stash
- **Options**: Filter by tag name or retrieve all

#### Get Stashbox List
- **Method**: `get_stashbox_list()`
- **Description**: Retrieves and configures stashbox connections
- **Features**:
  - Maps stashbox names to tag IDs
  - Retrieves connection endpoints
  - Validates stashbox availability

#### Extract FileSlim
- **Method**: `extract_fileslim()`
- **Description**: Extracts simplified file information from scene data
- **Extracted Data**:
  - File ID
  - Dimensions (width, height)
  - Codec
  - Size
  - Duration
  - Filename
  - Format
  - Fingerprints (oshash, phash)

## Command-Line Arguments

The program supports the following command-line arguments:

### `--delete_duplicates_scenes`
- **Description**: Delete duplicate scenes using Stash phash functionality
- **Behavior**: 
  - Runs with EXACT distance
  - Runs with HIGH distance
  - Commented out: MEDIUM and LOW distances
- **Mode**: Executes with dry_run=False (actual deletion)

### `--delete_duplicates_files`
- **Description**: Delete duplicate files within scenes using phash
- **Mode**: Executes with dry_run=False (actual deletion)

### `--process_files`
- **Description**: Process files for matches with stashbox databases
- **Behavior**:
  - Reads QueryMaxNumber from config (default: 3000)
  - Runs process_matches with parallel stashbox queries
- **Mode**: Executes with dry_run=False

### `--garbage`
- **Description**: Perform garbage collection activities
- **Operations**:
  1. Process corrupted scenes (delete scenes without phash)
  2. Process trash scenes (delete scenes in Trash directory)
  3. Remove match tags from organized scenes
  4. Remove false positive matches
- **Mode**: Executes with dry_run=False

### `--scan`
- **Description**: Trigger Stash metadata scan
- **Use Case**: Rescan library for new files

### `--update_scene_all`
- **Description**: Process and update all scenes with match tags
- **Behavior**:
  - Processes scenes from MATCH_STASHDB and MATCH_PORNDB
  - Currently limited to 2 scenes per stashbox (TODO: increase to 400)
- **Mode**: Executes with dry_run=False

### `--update_scene_path`
- **Description**: Process and update scenes in specific path(s)
- **Requires**: `--path` argument
- **Behavior**: Processes each provided path sequentially
- **Mode**: Executes with dry_run=False

### `--reset_scene_path`
- **Description**: Reset MATCH_DONE tag for scenes in specific path(s)
- **Requires**: `--path` argument
- **Behavior**: 
  - Runs 10 iterations per path
  - Processes 100 scenes per iteration
- **Mode**: Executes with dry_run=False

### `--test`
- **Description**: Run test operations
- **Behavior**: Executes process_test method for development/testing

### `--path`
- **Description**: Specify one or more directory paths to process
- **Used by**: `--update_scene_path`, `--reset_scene_path`
- **Format**: Space-separated list of paths
- **Example**: `--path "/path1" "/path2"`

## Usage Examples

### Delete duplicate scenes
```bash
python ManageStash.py --delete_duplicates_scenes
```

### Process files for matching
```bash
python ManageStash.py --process_files
```

### Update scenes in specific path
```bash
python ManageStash.py --update_scene_path --path "/videos/category1"
```

### Run garbage collection
```bash
python ManageStash.py --garbage
```

### Reset scene tags in path
```bash
python ManageStash.py --reset_scene_path --path "/videos/to-reprocess"
```

### Scan library
```bash
python ManageStash.py --scan
```

### Update all matched scenes
```bash
python ManageStash.py --update_scene_all
```

## Configuration

The program reads configuration from `App/config/config.toml` with the following sections:

### Stash_Host
- `Scheme`: HTTP/HTTPS scheme
- `Host`: Stash server hostname/IP
- `Port`: Stash server port
- `ApiKey`: Optional API key for authentication

### Path
- Various path configurations for operations like Trash directory

### Scenes
- `QueryMaxNumber`: Maximum number of scenes to query (default: 3000)

## Tag System

The program uses a specific tag system for tracking scene processing:

- **MATCH_FALSE**: Tag for false positive matches
- **MATCH_DONE**: Tag for processed scenes
- **MATCH_UNKNOWN**: Tag for unknown/unmatched scenes
- **MATCH_STASHDB**: Tag for matches found on stashdb.org
- **MATCH_PORNDB**: Tag for matches found on ThePornDB
- **MATCH_FANSDB**: Tag for matches found on FansDB
- **MATCH_PMV**: Tag for matches found on PMV Stash

## Constants

- `MATCHES_SCENES_PAGE`: 200 (scenes per page)
- `MATCHES_SCENES_MAX`: 400 (max scenes for matching)
- `MATCHES_SCENES_FALSE_POSITIVE_MAX`: 800 (max false positives to process)
- `MATCHES_SCENES_START_PAGE`: 1 (starting page number)
- `MATCHES_SCENES_INTERNAL_PAGE`: 50 (internal batch size)
- `SCENES_MAX`: 1000 (general max scenes limit)

## Logging

All operations include comprehensive logging with:
- Start/end markers for operations
- Progress tracking with intervals
- Error logging with retry information
- Statistics and summaries
- Dry-run mode indicators

## Error Handling

- Retry logic for failed API calls (3-5 retries)
- Sleep intervals between retries (4 seconds)
- Exception logging with GraphQL error details
- Graceful handling of missing data
