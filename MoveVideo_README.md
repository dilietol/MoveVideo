# MoveVideo

MoveVideo is a Python script designed to organize video files by moving them from a source directory to destination directories based on matching keys extracted from filenames and directory names.

## Features

- **Key-based File Organization**: Extracts keys from video file names and directory names to match and organize files.
- **Recursive Directory Search**: Searches for video files recursively within the input directory.
- **Directory Validation**: Validates that input and output directories exist and have appropriate permissions.
- **Small Directory Cleanup**: Automatically deletes small directories (below a specified size threshold) after processing.
- **Video File Verification**: Ensures only actual video files are moved, skipping non-video files.
- **Progress Tracking**: Provides progress indicators for large operations.

## How It Works

1. The script scans the input directory (`in`) for video files with extensions: `.mkv`, `.avi`, `.mp4`, `.wmv`, `.mov`, `.flv`.
2. For each video file, it extracts a key from the filename:
   - If the filename starts with `[tag]`, it uses the tag within the brackets.
   - Otherwise, it uses the part before the first dot or space.
3. It then searches for destination directories in the output directory (`out`).
4. For each destination directory, it extracts keys from the directory name by splitting on dots.
5. Files are moved from the input to the matching destination directory based on key matches.
6. Small directories (below `MIN_DIR_SIZE`) are deleted after processing.

## Configuration

The script uses a configuration class `MoveVideoConfig`:
- `in_dir`: Input directory path (default: "in")
- `out_dir`: Output directory path (default: "out")
- `min_dir_size`: Minimum directory size in bytes to keep (default: 1000)

## Usage

1. Place video files in the input directory (`in` by default).
2. Create destination directories within the output directory (`out` by default) with names containing keys.
3. Run the script:
   ```bash
   python MoveVideo.py
   ```
4. The script will organize the files and clean up small directories.

## Requirements

- Python 3.x
- `Log` module (assumed to be a custom logging utility)

## License

This project is licensed under the MIT License.
