import json
import os
import time
from typing import Any, List
from dataclasses import asdict, is_dataclass, dataclass

import logging
import configparser

from stashapi.stash_types import PhashDistance
from stashapi.stashapp import StashInterface

MATCHES_FALSE_POSITIVE = "MATCH_FALSE"  # Tag to add to scene when is not a match
MATCHES_FILTERED = ""  # Tag to use to filter scenes to process
MATCHES_DONE = "MATCH_DONE"  # Tag to add to scene when is processed
MATCHES_UNKNOWN = "UNKNOWN"  # Tag to add to scene when is unknown
MATCHES_SCENES_PAGE = 200
MATCHES_SCENES_MAX = 500
MATCHES_SCENES_START_PAGE = 1
SCENES_MAX = 1000


@dataclass
class StashBox:
    id: int
    name: str
    tag_name: str
    tag_id: int


@dataclass
class FileSlim:
    # File info
    id: int
    organized: bool
    width: int
    video_codec: float
    size: int
    duration: float


@dataclass
class DuplicatedFiles:
    # File comparison result
    files: List[FileSlim]  # list of files to compare
    id: int  # id of the file to keep
    why: str  # reason why the file was selected or not
    to_delete: List[int]  # list of files to delete
    to_delete_size: float  # size of files to delete


@dataclass
class Tags:
    id: int
    name: str


@dataclass
class Scene:
    id: int
    organized: bool
    tags: List[Tags]
    files: List[FileSlim]
    title: str = ""
    duplicated_files: DuplicatedFiles = None


@dataclass
class SceneFilter:
    organized: bool
    tags_includes: List[str]
    tags_excludes: List[str]
    file_count: int = 0


MATCHES_STASHBOX: List[StashBox] = [
    StashBox(name="stashdb.org", tag_name="MATCH_STASHDB", id=0, tag_id=0),
    StashBox(name="ThePornDB", tag_name="MATCH_PORNDB", id=0, tag_id=0),
    StashBox(name="PMV Stash", tag_name="MATCH_PMV", id=0, tag_id=0)
]

# Setup logger
logger = logging.getLogger("manage-stash")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(ch)


def log(msg):
    logger.info(msg)


def debug(msg):
    logger.debug(msg)


def log_block(msg, title):
    log_start(title)
    if isinstance(msg, list):
        log(" Number of elements: " + str(len(msg)))
        result = list()
        for elem in msg:
            if is_dataclass(elem):
                result.append(asdict(elem))
            else:
                result.append(elem)
        msg_formatted = json.dumps(result, indent=4)
    else:
        msg_formatted = json.dumps(msg, indent=4)
    logger.info(msg_formatted)
    log_end(title)


def log_end(title):
    log("********************** %s END **********************" % title)


def log_start(title):
    log("********************** %s START **********************" % title)


def parse_config():
    conf = configparser.ConfigParser()
    defaults_path = os.path.join('config', 'config.toml')
    conf.read(defaults_path)
    return conf


def initialize() -> (StashInterface, dict):
    global stash
    config = parse_config()
    # Set up Stash
    stash_args = {
        "scheme": config["Stash_Host"]["Scheme"],
        "host": config["Stash_Host"]["Host"],
        "port": config["Stash_Host"]["Port"]
    }
    if config["Stash_Host"]["ApiKey"]:
        stash_args["ApiKey"] = config["Host"]["ApiKey"]
    stash = StashInterface(stash_args)
    return stash, config["Path"]


def check_organized(array: list[FileSlim]):
    first_value = array[0].organized
    for elem in array:
        if elem.organized != first_value:
            return False
    return True


def check_duration(array: List[FileSlim]):
    first_value = float(array[0].duration)
    if first_value < 600:
        return False
    for elem in array:
        if abs((float(elem.duration) - first_value) / first_value) > 0.0005:
            return False
    return True


def select_by_width(files_dict: List[FileSlim]) -> List[FileSlim]:
    # Find the maximum value of the attribute "width"
    max_width = max(elem.width for elem in files_dict)

    # Select all occurrences with attribute 'width' equal to the maximum value
    matching_elements: list[FileSlim] = [elem for elem in files_dict if elem.width == max_width]
    return matching_elements


def select_by_codec(files_dict) -> List[FileSlim]:
    matching_elements_henvc: list[Any] = [elem for elem in files_dict if elem.video_codec == "hevc"]
    if len(matching_elements_henvc) >= 1:
        return matching_elements_henvc
    else:
        matching_elements: list[Any] = [elem for elem in files_dict if elem.video_codec == "h264"]
        if len(matching_elements) >= 1:
            return matching_elements
        else:
            matching_elements: list[Any] = [elem for elem in files_dict if elem.video_codec == "vc1"]
            if len(matching_elements) >= 1:
                return matching_elements
            else:
                matching_elements: list[Any] = [elem for elem in files_dict if elem.video_codec == "mpeg4"]
                if len(matching_elements) >= 1:
                    return matching_elements
                else:
                    matching_elements: list[Any] = [elem for elem in files_dict if elem.video_codec == "wmv3"]
                    if len(matching_elements) >= 1:
                        return matching_elements
    return []


def select_by_size(files_dict: List[FileSlim]) -> List[FileSlim]:
    max_value = max(files_dict, key=lambda x: x.size).size
    result = list(filter(lambda x: x.size == max_value, files_dict))
    return result


def select_the_best(files_dict: List[FileSlim]) -> DuplicatedFiles:
    result = DuplicatedFiles(files_dict, 0, "NA", [], 0)
    if len(files_dict) == 0:
        result.id = 0
        result.why = "No files"
        return result
    if len(files_dict) == 1:
        result.id = 0
        result.why = "No duplicates"
        return result
    organized_requested = not check_organized(files_dict)
    if not check_duration(files_dict):
        result.id = 0
        result.why = "Duration not valid"
        return result
    files_dict_2 = select_by_width(files_dict)
    if len(files_dict_2) == 0:
        result.id = 0
        result.why = "Not good width"
        return result
    elif len(files_dict_2) == 1:
        if organized_requested and not files_dict_2[0].organized:
            result.id = 0
            result.why = "Not all organized"
        else:
            result.id = files_dict_2[0].id
            result.why = "Best width"
            result.to_delete, result.to_delete_size = files_to_delete(files_dict, files_dict_2[0].id)
        return result
    files_dict_3 = select_by_codec(files_dict_2)
    if len(files_dict_3) == 0:
        result.id = 0
        result.why = "Not good codec"
        return result
    elif len(files_dict_3) == 1:
        if organized_requested and not files_dict_3[0].organized:
            result.id = 0
            result.why = "Not all organized"
        else:
            result.id = files_dict_3[0].id
            result.why = "Best codec"
            result.to_delete, result.to_delete_size = files_to_delete(files_dict, files_dict_3[0].id)
            return result
    files_dict_4 = select_by_size(files_dict_3)
    if len(files_dict_4) == 0:
        result.id = 0
        result.why = "Not good size"
        return result
    elif len(files_dict_4) == 1:
        if organized_requested and not files_dict_4[0].organized:
            result.id = 0
            result.why = "Not all organized"
        else:
            result.id = files_dict_4[0].id
            result.why = "Best size"
            result.to_delete, result.to_delete_size = files_to_delete(files_dict, files_dict_4[0].id)
        return result

    organized_one = [elem for elem in files_dict_4 if elem.organized]
    if len(organized_one) == 1:
        result.id = organized_one[0].id
        result.why = "One organized among equal files"
        result.to_delete, result.to_delete_size = files_to_delete(files_dict, organized_one[0].id)
    elif len(organized_one) > 1:
        result.id = organized_one[0].id
        result.why = "Selected among many organized equal files"
        result.to_delete, result.to_delete_size = files_to_delete(files_dict, organized_one[0].id)
    else:
        result.id = 0
        result.why = "No organized among equal file"
    return result


def files_to_delete(files_dict: list[FileSlim], best_file_id: int):
    return list(filter(lambda x: x != best_file_id, [elem.id for elem in files_dict])), round(
        (sum([elem.size for elem in files_dict if
              elem.id != best_file_id]) / 1024 / 1024 / 1024), 2)


def get_scene_duplicated_files(distance: PhashDistance, s: StashInterface) -> list[DuplicatedFiles]:
    # Duplicates
    log("REQUEST DUPLICATE SCENES FOUND")
    data = s.find_duplicate_scenes(distance=distance, fragment='...Scene')
    log("DUPLICATE SCENES FOUND")
    # log_block(data, "DUPLICATE SCENES DETAILS")
    compared_files_list: list[DuplicatedFiles] = []
    for element in data:
        duplicated_files_slim: list[FileSlim] = list()
        for item in element:
            file_slim = FileSlim(id=item.get("id"), organized=item.get("organized"),
                                 width=item.get("files")[0].get("width"),
                                 video_codec=item.get("files")[0].get("video_codec"),
                                 size=item.get("files")[0].get("size"),
                                 duration=item.get("files")[0].get("duration"))
            duplicated_files_slim.append(file_slim)
        compared_files_list.append(select_the_best(duplicated_files_slim))
    return compared_files_list


def delete_duplicates_scenes(s: StashInterface, p: PhashDistance = PhashDistance.EXACT, dry_run=True):
    log_start("DELETE DUPLICATES SCENES")
    log("Parameters: Distance %s - DryRun %s" % (p.name, dry_run))
    compared_files_list = get_scene_duplicated_files(p, s)
    # log_block(compared_files_list, "COMPARED FILES")

    deleted_size_sum = 0
    deleted_files_id_list: list[int] = []
    counters = {}
    counters_ok = {}
    for elem in compared_files_list:
        if elem.id != 0:
            deleted_size_sum += elem.to_delete_size
            deleted_files_id_list.extend(elem.to_delete)
            parameter = elem.why
            if parameter in counters_ok:
                counters_ok[parameter] += 1
            else:
                counters_ok[parameter] = 1
        else:
            parameter = elem.why
            if parameter in counters:
                counters[parameter] += 1
            else:
                counters[parameter] = 1
    array_of_files = []
    [array_of_files.extend(array.files) for array in compared_files_list]

    log("Dry run: " + str(dry_run))
    log("Number of comparison: " + str(len(compared_files_list)))
    log("Number of compared files: " + str(len(array_of_files)))
    log("Size to delete: " + str(deleted_size_sum))
    log("Number of files to delete: " + str(len(deleted_files_id_list)))
    log("counters for valid duplicates: " + json.dumps(counters_ok))
    log("counters for not valid duplicates: " + json.dumps(counters))

    for elem in deleted_files_id_list:
        if not dry_run:
            for i in range(3):
                try:
                    s.destroy_scene(elem, True)
                    log("File deleted: " + str(elem))
                    break
                except Exception as e:
                    log("FAILED TO DELETE SCENE %s" % elem)
                    print(f"Received a GraphQL exception : {e}")
                    time.sleep(4)
        else:
            log("File to delete: " + str(elem))
    log_end("DELETE DUPLICATES SCENES")


def get_tags(s: StashInterface, name: str = "") -> list[Tags]:
    """
    Retrieve a list of tags from the StashInterface object.
    Args:
        s (StashInterface): The StashInterface object to retrieve tags from.
        name (str): Optional. The name of the tag to filter by.
    Returns:
        list: A list of tag objects. If name is specified, only the matching tag(s) are returned.
    """
    result = list()
    # Retrieve all tags from the StashInterface object
    data = s.find_tags()

    # Filter the tags based on the specified name, if provided
    for elem in data:
        if elem["name"] == name or name == "":
            result.append(Tags(id=elem["id"], name=elem["name"]))

    return result


def get_stashbox_list(s: StashInterface, tags_list: list[Tags]) -> list[StashBox]:
    # Find stashbox
    stashbox_list: List[StashBox] = MATCHES_STASHBOX
    for stashbox in stashbox_list:
        for tag in tags_list:
            if stashbox.tag_name == tag.name:
                stashbox.tag_id = tag.id
    stashbox_connections = s.get_stashbox_connections()
    for elem in stashbox_connections:
        data = s.get_stashbox_connection(elem["endpoint"])
        elem["id"] = data["index"]
    for stashbox in stashbox_list:
        for conn in stashbox_connections:
            if stashbox.name == conn.get("name"):
                stashbox.id = conn.get("id")
    return stashbox_list


def update_tags(scene_list: List[Scene], s, dry_run=True):
    counter = 0
    for scene in scene_list:
        counter += 1
        if not dry_run:
            for i in range(3):
                try:
                    scene_id = s.update_scene({"id": scene.id, "tag_ids": ([tag.id for tag in scene.tags])})
                    log("UPDATED TAGs %s TO SCENE %s" % (",".join([tag.name for tag in scene.tags]), scene_id))
                    break
                except Exception as e:
                    log("FAILED TO UPDATE TAGS %s TO SCENE %s" % (",".join([tag.name for tag in scene.tags]), scene.id))
                    print(f"Received a GraphQL exception : {e}")
                    time.sleep(4)
        else:
            log("Tags to add: " + ",".join([tag.name for tag in scene.tags]) + " to scene: " + str(scene.id))
        if counter % 10 == 0:
            log("Scenes updated: " + str(counter))


def remove_tags(scene_list: List[Scene], s, tag_list: List[Tags], dry_run=True):
    for scene in scene_list:
        for tag_elem in tag_list:
            if tag_elem.name in [x.name for x in scene.tags]:
                scene.tags.remove(tag_elem)
    update_tags(scene_list, s, dry_run)


def find_scene_matches(s, scene_list: List[Scene], stashbox_list: List[StashBox], tag_list: List[Tags]) -> List[Scene]:
    # Scrape scenes
    scenes_counter = 0
    result: List[Scene] = list()
    log_start("FETCHING SCENE MATCHES")
    for scene in scene_list:
        new_scene = Scene(id=scene.id, organized=scene.organized, tags=scene.tags, files=list())
        scenes_counter += 1
        if scenes_counter % 10 == 0:
            log("Scenes processed: " + str(scenes_counter))
        found = False
        for stashbox in stashbox_list:
            data = None
            for i in range(10):
                try:
                    data = s.scrape_scene({"stash_box_index": stashbox.id}, {"scene_id": scene.id})
                except Exception as e:
                    log("FAILED TO SCRAPE SCENE %s FROM STASHBOX %s" % (scene.id, stashbox.name))
                    print(f"Received a GraphQL exception : {e}")
                    time.sleep(4)
                    data = None

            if data is not None:
                log("Scene %s found in %s" % (scene.id, stashbox.name))
                new_scene.tags.append(Tags(id=stashbox.tag_id, name=stashbox.tag_name))
                found = True
        if not found:
            log("Scene %s NOT found" % scene.id)
            new_scene.tags.extend([tag for tag in tag_list if
                                   tag.name == MATCHES_DONE])
        result.append(new_scene)
    log_end("FETCHING SCENE MATCHES")
    return result


def find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max=0) -> list[Scene]:
    scene_list = list()
    others = True
    page_number = MATCHES_SCENES_START_PAGE
    page_dim = MATCHES_SCENES_PAGE
    log_start("FETCHING SCENES")
    while others:
        if scenes_number_max == 0:
            page_dim = MATCHES_SCENES_PAGE
        elif (scenes_number_max - len(scene_list)) < MATCHES_SCENES_PAGE:
            page_dim = scenes_number_max - len(scene_list)
        log("Fetching page number " + str(page_number))
        data = s.find_scenes(f=scene_filter_str,
                             filter={"per_page": page_dim, "page": page_number, "sort": "id"},
                             get_count=False)
        # log_block(data, "Data")
        for elem in data:
            scene_list.append(Scene(id=elem["id"], organized=elem["organized"], title=elem["title"],
                                    tags=[Tags(id=tag["id"], name=tag["name"]) for tag in elem["tags"]],
                                    files=[FileSlim(id=file["id"], organized=elem["organized"],
                                                    width=file["width"], video_codec=file["video_codec"],
                                                    size=file["size"], duration=file["duration"]) for file in
                                           elem["files"]], duplicated_files=select_the_best(
                    [FileSlim(id=file["id"], organized=elem["organized"],
                              width=file["width"], video_codec=file["video_codec"],
                              size=file["size"], duration=file["duration"]) for file in
                     elem["files"]])))
        page_number += 1
        if len(scene_list) >= scenes_number_max != 0:
            others = False
        if data is None or len(data) == 0 or len(data) < page_dim:
            others = False
    log("Total fetched pages are " + str(page_number - 1) + " for " + str(len(scene_list)) + " scenes")
    log_end("FETCHING SCENES")
    return scene_list


def find_scenes_by_tags(s: StashInterface, tags_list: list[Tags], scene_filter: SceneFilter,
                        scenes_number_max) -> list[Scene]:
    # Find scenes
    scene_filter_str = {"organized": scene_filter.organized,
                        "tags":
                            {"value": [tag.id for tag in tags_list if tag.name in scene_filter.tags_includes],
                             "excludes": [tag.id for tag in tags_list if tag.name in scene_filter.tags_excludes],
                             "modifier": "INCLUDES_ALL",
                             "depth": 0
                             }
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)
    return scene_list


def find_scenes_by_included_tags(s: StashInterface, tags_list: list[Tags], scene_filter: SceneFilter,
                                 scenes_number_max) -> list[Scene]:
    # Find scenes
    scene_filter_str = {"organized": scene_filter.organized,
                        "tags":
                            {"value": [tag.id for tag in tags_list if tag.name in scene_filter.tags_includes],
                             "modifier": "INCLUDES",
                             "depth": 0
                             }
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)
    return scene_list


def find_scenes_by_filecount(s: StashInterface, scene_filter: SceneFilter,
                             scenes_number_max) -> list[Scene]:
    # Find scenes
    scene_filter_str = {"organized": scene_filter.organized,
                        "file_count": {"value": scene_filter.file_count, "modifier": "GREATER_THAN"}
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)
    return scene_list


def process_matches(s: StashInterface, dry_run=True):
    log_start("PROCESS MATCHES")
    # Retrieve all tags from the StashInterface object
    tags_list: List[Tags] = get_tags(s)
    # log_block(tags_list, "TAGS LIST")

    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)
    # log_block(stashbox_list, "STASHBOX LIST")

    scene_filter = SceneFilter(organized=False, tags_includes=[MATCHES_FILTERED],
                               tags_excludes=([x.tag_name for x in stashbox_list] + [MATCHES_FALSE_POSITIVE,
                                                                                     MATCHES_DONE]))
    scene_list = find_scenes_by_tags(s, tags_list, scene_filter, MATCHES_SCENES_MAX)
    # log_block(scene_list, "FIND SCENES")
    found_list: List[Scene] = []
    if len(scene_list) > 0:
        found_list = find_scene_matches(s, scene_list, stashbox_list, tags_list)
        # log_block(found_list, "MATCHES RESULT LIST")
    log("Number of matches found: " + str(
        len([elem.id for elem in found_list if
             any(y.name in [x.tag_name for x in stashbox_list] for y in elem.tags)])))

    update_tags(found_list, s, dry_run)
    log_end("PROCESS MATCHES")


def remove_matches(s: StashInterface, dry_run=True):
    log_start("REMOVE MATCHES")
    # Retrieve all tags from the StashInterface object
    tags_list: List[Tags] = get_tags(s)
    # log_block(tags_list, "TAGS LIST")

    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)
    # log_block(stashbox_list, "STASHBOX LIST")

    scene_filter = SceneFilter(organized=True,
                               tags_includes=[MATCHES_FILTERED] + [x.tag_name for x in stashbox_list] + [
                                   MATCHES_FALSE_POSITIVE, MATCHES_DONE, MATCHES_UNKNOWN],
                               tags_excludes=([]))
    scene_list = find_scenes_by_included_tags(s, tags_list, scene_filter, MATCHES_SCENES_MAX)
    # log_block(scene_list, "FIND SCENES")

    remove_tags(scene_list, s, [x for x in tags_list if
                                x.name in [y.tag_name for y in stashbox_list] or x.name in [MATCHES_FALSE_POSITIVE,
                                                                                            MATCHES_DONE,
                                                                                            MATCHES_UNKNOWN]], dry_run)
    log_end("REMOVE MATCHES")


def delete_duplicates_files(s: StashInterface, dry_run=True):
    log_start("DELETE DUPLICATES FILES")
    scene_filter = SceneFilter(organized=True, file_count=1, tags_includes=[],
                               tags_excludes=[])
    scene_list = find_scenes_by_filecount(s, scene_filter, MATCHES_SCENES_MAX)
    # log_block(scene_list, "FIND SCENES")

    deleted_size_sum = 0
    deleted_files_id_list: list[int] = []
    counters = {}
    counters_ok = {}
    for elem in scene_list:
        if elem.duplicated_files.id != 0:
            deleted_size_sum += elem.duplicated_files.to_delete_size
            deleted_files_id_list.extend(elem.duplicated_files.to_delete)
            parameter = elem.duplicated_files.why
            if parameter in counters_ok:
                counters_ok[parameter] += 1
            else:
                counters_ok[parameter] = 1
        else:
            parameter = elem.duplicated_files.why
            if parameter in counters:
                counters[parameter] += 1
            else:
                counters[parameter] = 1
    array_of_files = []
    [array_of_files.extend(array.duplicated_files.files) for array in scene_list]

    log("Dry run: " + str(dry_run))
    log("Number of comparison: " + str(len(scene_list)))
    log("Number of compared files: " + str(len(array_of_files)))
    log("Size to delete: " + str(deleted_size_sum))
    log("Number of files to delete: " + str(len(deleted_files_id_list)))
    log("counters for valid duplicates: " + json.dumps(counters_ok))
    log("counters for not valid duplicates: " + json.dumps(counters))

    for scene in scene_list:
        if scene.duplicated_files.id != 0:
            if not dry_run:
                if scene.duplicated_files.id != scene.files[0].id:
                    scene_id = s.update_scene({"id": scene.id, "primary_file_id": scene.duplicated_files.id})
                    log("File made primary: %s for scene: %s" % (str(scene.duplicated_files.id), scene_id))
                for file_id in scene.duplicated_files.to_delete:
                    s.destroy_files([file_id])
                    log("File deleted: " + str(file_id))
            else:
                for file_id in scene.duplicated_files.to_delete:
                    log("File to delete: " + str(file_id))
    log_end("DELETE DUPLICATES FILES")


def process_scan(s):
    log_start("PROCESS SCAN")
    s.metadata_scan()
    log_end("PROCESS SCAN")
    pass


def test_stash(s: StashInterface):
    """
    This function performs a series of actions using the given 'StashInterface' object.
    It retrieves the configuration, finds scenes, lists scrapers, lists connections,
    performs stashbox operations, identifies source configuration, and scrapes scenes.
    """

    # Configuration
    # data = s.get_configuration()
    # log_block(data, "CONFIGURATION")

    tags_list: list[Tags] = get_tags(s, "UNKNOWN")
    log_block(tags_list, "SELECTED TAGS")

    # Find scenes
    scene_filter1 = {"organized": True}
    scene_filter2 = {"tag_count": {"value": 0, "modifier": "EQUALS"}}
    scene_filter3 = {"tags": {"value": ["20"], "excludes": [], "modifier": "INCLUDES_ALL", "depth": 0}}
    scene_filter4 = {"tags": {"value": ["34"], "excludes": [], "modifier": "INCLUDES_ALL", "depth": 0}}
    data = s.find_scenes(f=scene_filter4, filter={"per_page": 10}, get_count=False)
    log_block(data, "SCENES")


def process_corrupted(s: StashInterface, scenes_number_max, dry_run=True):
    log_start("PROCESS CORRUPTED")
    scene_filter_str = {"phash_distance":
                            {"value": "0",
                             "modifier": "IS_NULL"}
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)
    # log_block(scene_list, "SCENES")

    log("Dry run: " + str(dry_run))
    log("Number of scenes: " + str(len(scene_list)))

    for scene in scene_list:
        if not dry_run:
            for i in range(3):
                try:
                    s.destroy_scene(scene.id, False)
                    log("DELETED SCENE %s" % scene.id)
                    break
                except Exception as e:
                    log("FAILED TO DELETE SCENE %s" % scene.id)
                    print(f"Received a GraphQL exception : {e}")
                    time.sleep(4)
        else:
            log("Scene to delete: " + str(scene.id))
    log_end("PROCESS CORRUPTED")


def process_trash(s: StashInterface, scenes_number_max, remote_paths, dry_run=True):
    log_start("PROCESS TRASH")
    scene_filter_str = {"path":
                            {"value": remote_paths["Trash"],
                             "modifier": "INCLUDES"}
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)
    # log_block(scene_list, "SCENES")

    log("Dry run: " + str(dry_run))
    log("Number of scenes: " + str(len(scene_list)))

    for scene in scene_list:
        if not dry_run:
            for i in range(3):
                try:
                    s.destroy_scene(scene.id, True)
                    log("DELETED SCENE %s" % scene.id)
                    break
                except Exception as e:
                    log("FAILED TO DELETE SCENE %s" % scene.id)
                    print(f"Received a GraphQL exception : {e}")
                    time.sleep(4)
        else:
            log("Scene to delete: " + str(scene.id))
    log_end("PROCESS TRASH")


if __name__ == "__main__":
    # TODO delete Shoko integration in an other class
    # TODO Scheduling all the programs
    # TODO reorganize the log call for the three programs
    # TODO unify the logging anc configuration system

    stash, paths = initialize()

    delete_duplicates_scenes(stash, PhashDistance.EXACT, False)
    # delete_duplicates_scenes(stash, PhashDistance.HIGH, True)
    # delete_duplicates_scenes(stash, PhashDistance.MEDIUM, True)
    delete_duplicates_files(stash, False)
    process_corrupted(stash, SCENES_MAX, False)
    process_trash(stash, SCENES_MAX, paths, False)
    process_matches(stash, False)
    remove_matches(stash, False)
    process_scan(stash)
    # test_stash(stash)
