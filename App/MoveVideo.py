import os
import shutil
import sys
from collections import namedtuple
from pathlib import Path
from typing import List

from Log import Logger

VERSION = "0.1"


# Convert to proper class-based configuration
class MoveVideoConfig:
    def __init__(self, in_dir="in", out_dir="out", min_dir_size=1000):
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.min_dir_size = min_dir_size
        self.validate_directories()

    def validate_directories(self):
        # Verify input directory
        if not os.path.exists(self.in_dir):
            raise ValueError(f"Input directory {self.in_dir} does not exist")
        if not os.path.isdir(self.in_dir):
            raise ValueError(f"Input path {self.in_dir} is not a directory")
        if not os.access(self.in_dir, os.R_OK):
            raise PermissionError(f"No read permission for input directory {self.in_dir}")

        # Verify output directory
        if not os.path.exists(self.out_dir):
            raise ValueError(f"Output directory {self.out_dir} does not exist")
        if not os.path.isdir(self.out_dir):
            raise ValueError(f"Output path {self.out_dir} is not a directory")
        if not os.access(self.out_dir, os.W_OK):
            raise PermissionError(f"No write permission for output directory {self.out_dir}")

class MoveVideo:
    def __init__(self):
        self.logger = Logger("MoveVideo")
        self.config = MoveVideoConfig()
        self.dir_in = self.config.in_dir
        self.dir_out = self.config.out_dir
        self.min_dir_size = self.config.min_dir_size

    def get_directory_size(self, directory_path):
        total_size = 0
        with os.scandir(directory_path) as it:
            for entry in it:
                if entry.is_file():
                    total_size += entry.stat().st_size
                elif entry.is_dir():
                    total_size += self.get_directory_size(entry.path)
        return total_size

    def delete_small_directories(self, directory_path):
        self.logger.log_start(f"Deleting small directories in {directory_path}")
        for root, dirs, files in os.walk(directory_path):
            for dir_name in dirs:
                dir_path = os.path.join(str(root), str(dir_name))
                size = self.get_directory_size(dir_path)
                self.logger.log(f"Size {dir_path} is {size} bytes")
                if size < self.min_dir_size:
                    for file_name in os.listdir(dir_path):
                        file_path = os.path.join(dir_path, file_name)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            self.logger.log(f"Deleting {file_path}")
                    self.logger.log(f"Deleting {dir_path} with size {size} bytes")
                    os.rmdir(dir_path)
        self.logger.log_end(f"Deleting small directories in {directory_path}")

    def generate_source_list(self):
        Item = namedtuple("Item", ["File", "Path", "Key"])
        item_list: List[Item] = list()

        # Search for all video files recursively within the DIR_IN directory
        # and save the file name, full path and file key in the list of "Item" objects
        video_extensions = ['*.mkv', '*.avi', '*.mp4', '*.wmv', '*.mov', '*.flv']
        for ext in video_extensions:
            for txt_file in Path(self.dir_in).rglob(ext):
                key: str = self.extract_key_from_filename(txt_file.name)
                item_list.append(Item(txt_file.name, txt_file, key.lower()))
        return item_list

    @staticmethod
    def generate_destination_list(dir_out):
        Item = namedtuple("Item", ["Dir", "Path", "Key"])
        item_list: List[Item] = list()
        p = Path(dir_out)

        # Search for all directories or symlinks present in the DIR_OUT directory.
        # For each found directory name, extract keys from the directory name
        # and save them in the list of "Item" objects
        for txt_file in [f for f in p.iterdir() if (f.is_dir() or f.is_symlink())]:
            keys = MoveVideo.extract_keys_from_directory_name(txt_file.name)
            for key in keys:
                if key.startswith("_"):
                    # Remove underscore for directories with multi group (starting with underscore)
                    item_list.append(Item(txt_file.name, txt_file, key[1:]))
                else:
                    item_list.append(Item(txt_file.name, txt_file.resolve(), key))
                    if key.endswith("N"):
                        # Calculate also key for collection based on N (ending with N)
                        item_list.append(Item(txt_file.name, txt_file.resolve(), key[:-1]))
        return item_list

    @staticmethod
    def extract_key_from_filename(file_in):
        # If it starts with [tag], use the tag between square brackets
        if file_in.startswith('['):
            end_bracket = file_in.find(']')
            if end_bracket != -1:
                return file_in[1:end_bracket]

        # Otherwise, use the part before the first dot or space
        parts = file_in.split('.')
        alt_parts = file_in.split(' ')

        # Choose between the two methods based on length
        if len(alt_parts) > 0 and (len(alt_parts[0]) < len(parts[0]) or len(parts) == 1):
            return alt_parts[0]
        else:
            return parts[0]

    @staticmethod
    def extract_keys_from_directory_name(file_in):
        result = list()
        keys = file_in.split('.')
        for sub in keys:
            key = sub.strip().lower()
            result.append(key)
            if key[-1] == 'n':
                # Add also the key for the collection based on N (ends with N)
                result.append(key[:-1])
        return result

    @staticmethod
    def is_video_file(file_path):
        """Verify if the file is actually a video file"""
        try:
            # Extract extension
            _, ext = os.path.splitext(file_path)
            video_extensions = ['.mkv', '.avi', '.mp4', '.wmv', '.mov', '.flv']
            return ext.lower() in video_extensions
        except Exception:
            return False

    def move_files(self, dir_out):
        self.logger.log_start(f"Moving files from {self.dir_in} to {dir_out}")
        source_list = self.generate_source_list()
        destination_list = self.generate_destination_list(dir_out)

        # Verify that there are files to move
        if not source_list:
            self.logger.log("No video files found in source directory")
            return
        else:
            self.logger.log(f"Found {len(source_list)} video files in source directory")

        # Verify that there are destination directories
        if not destination_list:
            self.logger.log("No destination directories found")
            return
        else:
            self.logger.log(f"Found {len(destination_list)} destination directories")

        source_key_list = [sub.Key for sub in source_list]
        source_filename_list = [sub.File for sub in source_list]
        destination_key_list = [sub.Key for sub in destination_list]

        self.logger.log("Source filenames:")
        self.logger.log(source_filename_list)
        self.logger.log("Source keys:")
        self.logger.log(source_key_list)

        found_key_list = list(set(source_key_list) & set(destination_key_list))
        missing_key_list = list(set(source_key_list) - set(destination_key_list))

        self.logger.log("Found keys:")
        self.logger.log(found_key_list)
        self.logger.log("Missing keys:")
        self.logger.log(missing_key_list)

        # Add progress indicator for large operations
        total_keys = len(found_key_list)
        processed_count = 0
        for key_name in found_key_list:
            destination_dir = [x.Path for x in destination_list if x.Key == key_name]
            source_files = [x.Path for x in source_list if x.Key == key_name]

            if not destination_dir:
                self.logger.log(f"No destination directory found for key {key_name}")
                continue

            for source_file in source_files:
                try:
                    # Verify that the file is actually a video
                    if not self.is_video_file(source_file):
                        self.logger.log(f"Skipping non-video file: {source_file}")
                        continue

                    destination_file = os.path.join(str(Path(destination_dir[0])), source_file.name)
                    shutil.move(str(Path(source_file)), destination_file)
                    self.logger.log(f"Moved {source_file} to {destination_file}")
                except Exception as e:
                    self.logger.log(f"Error moving {source_file}: {str(e)}")

            processed_count += 1
            self.logger.log(f"Processed {processed_count}/{total_keys} keys")

        self.logger.log_end(f"Moving files from {self.dir_in} to {dir_out}")

        sys.stdout.flush()

    @staticmethod
    def get_subdirectories_with_prefix(directory):
        subdirectories = []
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir():
                    subdirectories.append(entry.path)
        return subdirectories

    def main(self):
        self.logger.log("Version: " + str(VERSION))

        self.move_files(self.dir_out)
        self.delete_small_directories(self.dir_in)

if __name__ == '__main__':
    move_video = MoveVideo()
    move_video.main()
