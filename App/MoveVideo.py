import os
import shutil
import sys
from collections import namedtuple
from pathlib import Path
from typing import List

VERSION = "0.1"

DIR_IN = "in"
DIR_OUT = "out"

if not os.path.isdir(DIR_IN):
    raise Exception(f"Directory {DIR_IN} does not exist")

if not os.path.isdir(DIR_OUT):
    raise Exception(f"Directory {DIR_OUT} does not exist")

def generate_source_list():
    Item = namedtuple("Item", ["File", "Path", "Key"])
    item_list: List[Item] = list()

    # Cerca tutti i file .mkv, .avi e .mp4 in modo ricorsivo all'interno della directory DIR_IN
    # e salva il nome del file, il percorso completo e la chiave del file nella lista degli oggetti "Item"
    for txt_file in Path(DIR_IN).rglob('*.mkv'):
        key: str = extract_key_from_filename(txt_file.name)
        item_list.append(Item(txt_file.name, txt_file, key.lower()))
    for txt_file in Path(DIR_IN).rglob('*.avi'):
        key: str = extract_key_from_filename(txt_file.name)
        item_list.append(Item(txt_file.name, txt_file, key.lower()))
    for txt_file in Path(DIR_IN).rglob('*.mp4'):
        key: str = extract_key_from_filename(txt_file.name)
        item_list.append(Item(txt_file.name, txt_file, key.lower()))
    return item_list


def generate_destination_list():
    Item = namedtuple("Item", ["Dir", "Path", "Key"])
    item_list: List[Item] = list()
    p = Path(DIR_OUT)

    # Cerca tutte le directory o i symlink presenti nella directory DIR_OUT.
    # Per ogni nome di directory trovato, estrae le chiavi dal nome della directory
    # e le salva nella lista degli oggetti "Item"
    for txt_file in [f for f in p.iterdir() if (f.is_dir() or f.is_symlink())]:
        keys = extract_keys_from_directory_name(txt_file.name)
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
    if file_in.find('[') == 0:
        if file_in.find(']') != -1:
            # Se il nome del file inizia con "[", allora assume che ci sia una chiave tra parentesi quadre
            result = file_in[file_in.find('[') + 1:file_in.find(']')]
            return result
    keys = file_in.split('.')
    return keys[0]


def extract_keys_from_directory_name(file_in):
    result = list()
    keys = file_in.split('.')
    for sub in keys:
        key = sub.strip().lower()
        result.append(key)
        if key[-1] == 'n':
            # Aggiungi anche la chiave per la collezione basata su N (termina con N)
            result.append(key[:-1])
    return result


if __name__ == '__main__':
    print("Version: " + str(VERSION))

    # Genera la lista dei file sorgente e stampa i nomi dei file e le relative chiavi
    source_list = generate_source_list()
    source_key_list = [sub.Key for sub in source_list]
    source_filename_list = [sub.File for sub in source_list]
    print("Source filenames:")
    print(source_filename_list)
    print("Source keys:")
    print(source_key_list)

    # Genera la lista delle directory di destinazione e stampa i nomi delle directory e le relative chiavi
    destination_list = generate_destination_list()
    destination_dir_list = [sub.Dir for sub in destination_list]
    destination_key_list = [sub.Key for sub in destination_list]
    print("Destination directories:")
    print(destination_dir_list)
    print("Destination keys:")
    print(destination_key_list)

    # Cerca le chiavi che si trovano sia nella lista sorgente che in quella di destinazione
    # e stampa le chiavi trovate e quelle mancanti
    found_key_list = list(set(source_key_list) & set(destination_key_list))
    missing_key_list = list(set(source_key_list) - set(destination_key_list))
    print("Found keys:")
    print(found_key_list)
    print("Missing keys:")
    print(missing_key_list)
    sys.stdout.flush()

    for key_name in found_key_list:
        destination_dir = [x.Path for x in destination_list if x.Key == key_name]
        source_files = [x.Path for x in source_list if x.Key == key_name]
        for x in source_files:
            shutil.move(str(Path(x)), os.path.join(str(Path(destination_dir[0])), os.path.basename(x)))
            print(r"Moved " + str(Path(x)) + " in " + str(Path(destination_dir[0])))
            # print(r"Fake moving " + str(Path(x)) + " in " + str(Path(destination_dir[0])))
            sys.stdout.flush()
