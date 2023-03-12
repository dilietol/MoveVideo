# This is a sample Python script.
import shutil
from collections import namedtuple
from pathlib import Path
from typing import List



DIR_IN = "movevideo_in"
DIR_OUT = "movevideo_out"


def generate_source_list():
    Item = namedtuple("Item", ["File", "Path", "Key"])
    item_list: List[Item] = list()
    for txt_file in Path(DIR_IN).rglob('*.mkv'):
        key: str = extract_key_from_filename(txt_file.name)
        item_list.append(Item(txt_file.name, txt_file, key))
    for txt_file in Path(DIR_IN).rglob('*.avi'):
        key: str = extract_key_from_filename(txt_file.name)
        item_list.append(Item(txt_file.name, txt_file, key))
    return item_list


def generate_destination_list():
    Item = namedtuple("Item", ["Dir", "Path", "Key"])
    item_list: List[Item] = list()
    p = Path(DIR_OUT)
    for txt_file in [f for f in p.iterdir() if (f.is_dir() or f.is_symlink())]:
        keys = extract_keys_from_dirname(txt_file.name)
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


def extract_key_from_filename(file_in):
    keys = file_in.split('.')
    return keys[0]


def extract_keys_from_dirname(file_in):
    keys = file_in.split('-')
    return [sub.strip() for sub in keys]


if __name__ == '__main__':
    source_list = generate_source_list()
    source_key_list = [sub.Key for sub in source_list]
    source_filename_list = [sub.File for sub in source_list]
    print("Source filenames:")
    print(source_filename_list)
    print("Source keys:")
    print(source_key_list)

    destination_list = generate_destination_list()
    destination_dir_list = [sub.Dir for sub in destination_list]
    destination_key_list = [sub.Key for sub in destination_list]
    print("Destination directories:")
    print(destination_dir_list)
    print("Destination keys:")
    print(destination_key_list)

    found_key_list = list(set(source_key_list) & set(destination_key_list))
    missing_key_list = list(set(source_key_list) - set(destination_key_list))
    print("Found keys:")
    print(found_key_list)
    print("Missing keys:")
    print(missing_key_list)

    for key_name in found_key_list:
        destination_dir = [x.Path for x in destination_list if x.Key == key_name]
        source_files = [x.Path for x in source_list if x.Key == key_name]
        for x in source_files:
            shutil.move(str(Path(x)), str(Path(destination_dir[0])))
            print(r"Moved " + str(Path(x)) + " in " + str(Path(destination_dir[0])))
            # print(r"Fake moving " + str(Path(x)) + " in " + str(Path(destination_dir[0])))
