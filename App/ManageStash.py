import argparse
import concurrent.futures
import configparser
import json
import logging
import os
import time
from dataclasses import asdict, is_dataclass, dataclass, field
from typing import List

from stashapi.stash_types import PhashDistance
from stashapi.stashapp import StashInterface

from FindBestFile import FileSlim, DuplicatedFiles

MATCHES_FALSE_POSITIVE = "MATCH_FALSE"  # Tag to add to scene when is not a match
MATCHES_FILTERED = ""  # Tag to use to filter scenes to process
MATCHES_DONE = "MATCH_DONE"  # Tag to add to scene when is processed
MATCHES_UNKNOWN = "UNKNOWN"  # Tag to add to scene when is unknown
MATCHES_SCENES_PAGE = 200
MATCHES_SCENES_MAX = 200
MATCHES_SCENES_START_PAGE = 1
MATCHES_SCENES_INTERNAL_PAGE = 50
SCENES_MAX = 1000


@dataclass
class StashBox:
    id: int
    name: str
    tag_name: str
    tag_id: int
    url: str = None


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
    duplicated_files: DuplicatedFiles = field(init=False)

    def __post_init__(self) -> None:
        self.duplicated_files = DuplicatedFiles(files=self.files)


@dataclass
class SceneFilter:
    organized: bool
    tags_includes: List[str]
    tags_excludes: List[str]
    file_count: int = 0


@dataclass
class Fingerprints:
    json: str
    algorithm: str = field(init=False)
    hash: str = field(init=False)
    duration: int = field(init=False)

    def __post_init__(self) -> None:
        self.algorithm = self.json["algorithm"]
        self.hash = self.json["hash"]
        self.duration = self.json["duration"]
        self.json = None


@dataclass
class Studio:
    json: str
    stored_id: str = field(init=False)
    name: str = field(init=False)
    url: str = field(init=False)
    parent: str = field(init=False)
    image: str = field(init=False)
    remote_site_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.stored_id = self.json["stored_id"]
        self.name = self.json["name"]
        self.url = self.json["url"]
        self.parent = self.json["parent"]
        self.image = self.json["image"]
        self.remote_site_id = self.json["remote_site_id"]
        self.json = None


@dataclass
class Performer:
    json: str
    stored_id: str = field(init=False)
    name: str = field(init=False)
    disambiguation: str = field(init=False)
    gender: str = field(init=False)
    url: str = field(init=False)
    twitter: str = field(init=False)
    instagram: str = field(init=False)
    birthdate: str = field(init=False)
    ethnicity: str = field(init=False)
    country: str = field(init=False)
    eye_color: str = field(init=False)
    height: str = field(init=False)
    measurements: str = field(init=False)
    fake_tits: str = field(init=False)
    penis_length: str = field(init=False)
    circumcised: str = field(init=False)
    career_length: str = field(init=False)
    tattoos: str = field(init=False)
    piercings: str = field(init=False)
    aliases: str = field(init=False)
    images: List[str] = field(init=False)
    details: str = field(init=False)
    death_date: str = field(init=False)
    hair_color: str = field(init=False)
    weight: str = field(init=False)
    remote_site_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.stored_id = self.json["stored_id"]
        self.name = self.json["name"]
        self.disambiguation = self.json["disambiguation"]
        self.gender = self.json["gender"]
        self.url = self.json["url"]
        self.twitter = self.json["twitter"]
        self.instagram = self.json["instagram"]
        self.birthdate = self.json["birthdate"]
        self.ethnicity = self.json["ethnicity"]
        self.country = self.json["country"]
        self.eye_color = self.json["eye_color"]
        self.height = self.json["height"]
        self.measurements = self.json["measurements"]
        self.fake_tits = self.json["fake_tits"]
        self.penis_length = self.json["penis_length"]
        self.circumcised = self.json["circumcised"]
        self.career_length = self.json["career_length"]
        self.tattoos = self.json["tattoos"]
        self.piercings = self.json["piercings"]
        self.aliases = self.json["aliases"]
        self.images = self.json["images"]
        self.details = self.json["details"]
        self.death_date = self.json["death_date"]
        self.hair_color = self.json["hair_color"]
        self.weight = self.json["weight"]
        self.remote_site_id = self.json["remote_site_id"]
        self.json = None


# TODO: complete this dataclass
@dataclass
class Match:
    json: str
    title: str = field(init=False)
    code: str = field(init=False)
    details: str = field(init=False)
    director: str = field(init=False)
    urls: List[str] = field(init=False)
    date: str = field(init=False)
    image: str = field(init=False)
    file: str = field(init=False)
    studio: Studio = field(init=False)
    performers: List[Performer] = field(init=False)
    remote_site_id: str = field(init=False)
    duration: int = field(init=False)
    fingerprints: List[Fingerprints] = field(init=False)

    def __post_init__(self) -> None:
        self.title = self.json["title"]
        self.code = self.json["code"]
        self.details = self.json["details"]
        self.director = self.json["director"]
        self.date = self.json["date"]
        self.urls = self.json["urls"]
        self.image = None  # TODO: add image
        self.file = self.json["file"]
        self.studio = Studio(json=self.json["studio"])
        self.performers = [Performer(json=p) for p in self.json["performers"]] if self.json[
                                                                                      "performers"] is not None else []
        self.remote_site_id = self.json["remote_site_id"]
        self.duration = self.json["duration"]
        self.fingerprints = [Fingerprints(json=f) for f in self.json["fingerprints"]]
        self.json = None  # TODO: remove for problem determination


@dataclass
class Scrape:
    s: StashInterface
    scene: Scene
    stashbox: StashBox
    matches: List[Match] = field(init=False)

    def __post_init__(self) -> None:
        self.matches = find_matches(self.s, self.scene, self.stashbox)
        self.s = None


MATCHES_STASHBOX: List[StashBox] = [
    StashBox(name="stashdb.org", tag_name="MATCH_STASHDB", id=0, tag_id=0),
    StashBox(name="ThePornDB", tag_name="MATCH_PORNDB", id=0, tag_id=0),
    StashBox(name="PMV Stash", tag_name="MATCH_PMV", id=0, tag_id=0),
    StashBox(name="FansDB", tag_name="MATCH_FANSDB", id=0, tag_id=0)
]

# Setup logger
logger = logging.getLogger("manage-stash")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
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
    # TODO reorganize stash interface in order to move this initialization in a package/file in the future and move there all the method that use stash interface; leaving in this file only the processing methods.
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


def get_scene_duplicated_files(distance: PhashDistance, s: StashInterface) -> list[DuplicatedFiles]:
    log("DUPLICATE SCENES FOUND REQUEST")
    data = s.find_duplicate_scenes(distance=distance, fragment='...Scene')
    log("DUPLICATE SCENES FOUND RESPONSE")
    # log_block(data, "DUPLICATE SCENES DETAILS")
    compared_files_list: list[DuplicatedFiles] = []
    for element in data:
        duplicated_files_slim: list[FileSlim] = list()
        for item in element:
            file_slim = extract_fileslim(item)
            duplicated_files_slim.append(file_slim)
        compared_files_list.append(DuplicatedFiles(files=duplicated_files_slim))
    return compared_files_list


def extract_fileslim(item) -> FileSlim:
    # TODO manage multiple files
    phash = oshash = None
    for elem in item.get("files")[0].get("fingerprints"):
        if elem.get("type") == "phash":
            phash = elem.get("value")
        if elem.get("type") == "oshash":
            oshash = elem.get("value")
    return FileSlim(id=item.get("id"), organized=item.get("organized"),
                    width=item.get("files")[0].get("width"),
                    video_codec=item.get("files")[0].get("video_codec"),
                    size=item.get("files")[0].get("size"),
                    duration=item.get("files")[0].get("duration"),
                    basename=item.get("files")[0].get("basename"),
                    format=item.get("files")[0].get("format"),
                    oshash=oshash,
                    phash=phash
                    )


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

    # TODO refactor in order to use the destroy_scenes method
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
        elem["url"] = elem["endpoint"]
    for stashbox in stashbox_list:
        for conn in stashbox_connections:
            if stashbox.name == conn.get("name"):
                stashbox.id = conn.get("id")
                stashbox.url = conn.get("url")
    return stashbox_list


def update_tags(scene_list: List[Scene], s: StashInterface, dry_run=True):
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


def remove_tags(scene_list: List[Scene], s: StashInterface, tag_list: List[Tags], dry_run=True):
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
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(call_stash_api, new_scene, s, scene, stashbox) for stashbox in stashbox_list]
            for future in concurrent.futures.as_completed(futures):
                found = found or future.result()
        if not found:
            log("Scene %s NOT found" % scene.id)
            new_scene.tags.extend([tag for tag in tag_list if
                                   tag.name == MATCHES_DONE])
        result.append(new_scene)
    log_end("FETCHING SCENE MATCHES")
    return result


def call_stash_api(new_scene, s, scene, stashbox) -> bool:
    data = None
    found = False
    for i in range(3):
        try:
            data = s.scrape_scene({"stash_box_index": stashbox.id}, {"scene_id": scene.id})
            break
        except Exception as e:
            log("FAILED TO SCRAPE SCENE %s FROM STASHBOX %s" % (scene.id, stashbox.name))
            print(f"Received a GraphQL exception : {e}")
            time.sleep(4)
            data = None
    if data is not None:
        log("Scene %s found in %s" % (scene.id, stashbox.name))
        new_scene.tags.append(Tags(id=stashbox.tag_id, name=stashbox.tag_name))
        found = True
    return found


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
                                    files=[extract_fileslim(elem)]))
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


def find_scenes_by_included_all_tags(s: StashInterface, tags_list: list[Tags], scene_filter: SceneFilter,
                                     scenes_number_max) -> list[Scene]:
    # Find scenes
    scene_filter_str = {"organized": scene_filter.organized,
                        "tags":
                            {"value": [tag.id for tag in tags_list if tag.name in scene_filter.tags_includes],
                             "modifier": "INCLUDES_ALL",
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
    for i in range(0, len(scene_list), MATCHES_SCENES_INTERNAL_PAGE):
        log("List group iterator: " + str(i))
        scene_list_page = scene_list[i:i + MATCHES_SCENES_INTERNAL_PAGE]
        found_list = find_scene_matches(s, scene_list_page, stashbox_list, tags_list)
        # log_block(found_list, "MATCHES RESULT LIST")
        log("Number of matches found: " + str(
            len([elem.id for elem in found_list if
                 any(y.name in [x.tag_name for x in stashbox_list] for y in elem.tags)])))

        update_tags(found_list, s, dry_run)
    log_end("PROCESS MATCHES")


def process_test(s: StashInterface, dry_run=True):
    # TODO: Complete the test. Use this method to test new code and API call
    log_start("PROCESS Test")
    # Retrieve all tags from the StashInterface object
    tags_list: List[Tags] = get_tags(s)

    log_block(tags_list, "TAGS LIST")
    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)
    log_block(stashbox_list, "STASHBOX LIST")

    for stashbox in filter(lambda x: x.tag_name in ["MATCH_STASHDB", "MATCH_PORNDB"], stashbox_list):
        scrape_create_performer_studio_for_stash(s, stashbox, tags_list, 20)

    log_end("PROCESS Test")


def scrape_create_performer_studio_for_stash(s: StashInterface, stashbox: StashBox, tags_list, scenes_number_max=20):
    scene_filter = SceneFilter(organized=False, tags_includes=[stashbox.tag_name],
                               tags_excludes=([MATCHES_FALSE_POSITIVE]))
    scene_list = find_scenes_by_tags(s, tags_list, scene_filter, scenes_number_max)
    # log_block(scene_list, "FIND SCENES")
    log_start("SCRAPE SCENE for stashbox: " + stashbox.name)
    scrape_list: List[Scrape] = []
    for scene in scene_list:
        scrape = Scrape(s, scene, stashbox)
        scrape_list.append(scrape)
        log(scrape)
        for match in scrape.matches:
            log(match)
            for performer in match.performers:
                log(performer)
                if performer.stored_id is None:
                    create_performer(s, stashbox, performer)
            studio: Studio = match.studio
            log(studio)
            if studio.stored_id is None:
                create_studio(s, stashbox, studio)
    log_end("SCRAPE SCENE for stashbox: " + stashbox.name)


def create_studio(s: StashInterface, stashbox: StashBox, studio: Studio) -> None:
    s.create_studio(
        {"name": studio.name, "url": studio.url,
         "parent_id": studio.parent.get("stored_id") if studio.parent is not None else None,
         "image": studio.image,
         "stash_ids": [{"endpoint": stashbox.url, "stash_id": studio.remote_site_id}]})
    log("STUDIO CREATED: " + studio.name)


def create_performer(s: StashInterface, stashbox: StashBox, performer: Performer) -> None:
    s.create_performer(
        {"name": performer.name, "disambiguation": performer.disambiguation, "url": performer.url,
         "gender": performer.gender, "birthdate": performer.birthdate, "ethnicity": performer.ethnicity,
         "country": performer.country, "eye_color": performer.eye_color, "height_cm": performer.height,
         "measurements": performer.measurements, "fake_tits": performer.fake_tits,
         "penis_length": performer.penis_length, "circumcised": performer.circumcised,
         "career_length": performer.career_length, "tattoos": performer.tattoos,
         "piercings": performer.piercings,
         "alias_list": performer.aliases.split(",") if performer.aliases is not None else [],
         "twitter": performer.twitter, "instagram": performer.instagram,
         "favorite": False, "image": performer.images[0] if len(performer.images) > 0 else None,
         "details": performer.details, "death_date": performer.death_date,
         "hair_color": performer.hair_color, "weight": performer.weight,
         "stash_ids": [{"endpoint": stashbox.url, "stash_id": performer.remote_site_id}]})
    log("PERFORMER CREATED: " + performer.name)


def find_matches(s: StashInterface, scene: Scene, stashbox: StashBox) -> List[Match]:
    """
    Finds matches for a given scene and stashbox by scraping data.

    Args:
        s (StashInterface): The interface used for scraping.
        scene (Scene): The scene to find matches for.
        stashbox (StashBox): The stashbox to search for matches.

    Returns:
        List[Match]: A list of matches found for the scene and stashbox.
    """
    data = None
    result: List[Match] = list()

    # Try scraping the scene data up to 3 times
    for _ in range(3):
        try:
            data = s.scrape_scene({"stash_box_index": stashbox.id}, {"scene_id": scene.id})
            break
        except Exception as e:
            log("FAILED TO SCRAPE SCENE %s FROM STASHBOX %s" % (scene.id, stashbox.name))
            print(f"Received a GraphQL exception : {e}")
            time.sleep(4)
            data = None

    if data is not None:
        # Process the scraped data and create Match objects
        for elem in data:
            result.append(Match(json=elem))
    else:
        log("Scene %s NOT found" % scene.id)

    return result


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


def remove_false_matches(s: StashInterface, dry_run=True):
    log_start("REMOVE FALSE MATCHES")
    # Retrieve all tags from the StashInterface object
    tags_list: List[Tags] = get_tags(s)
    # log_block(tags_list, "TAGS LIST")

    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)
    # log_block(stashbox_list, "STASHBOX LIST")

    scene_filter = SceneFilter(organized=False,
                               tags_includes=[MATCHES_FALSE_POSITIVE, MATCHES_DONE],
                               tags_excludes=([]))
    scene_list = find_scenes_by_included_all_tags(s, tags_list, scene_filter, MATCHES_SCENES_MAX)

    remove_tags(scene_list, s, [x for x in tags_list if
                                x.name in [y.tag_name for y in stashbox_list] or x.name in [MATCHES_DONE]], dry_run)

    log_end("REMOVE FALSE MATCHES")
    pass


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

    if len(scene_list) == 0:
        log("No scenes to delete")
    else:
        destroy_scenes(s, dry_run, scene_list, False)
    log_end("PROCESS CORRUPTED")


def process_trash(s: StashInterface, scenes_number_max, remote_paths, dry_run=True):
    log_start("PROCESS TRASH")
    scene_filter_str = {"path":
                            {"value": remote_paths["Trash"],
                             "modifier": "INCLUDES"}
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)

    if len(scene_list) == 0:
        log("No scenes to delete")
    else:
        destroy_scenes(s, dry_run, scene_list, True)
    log_end("PROCESS TRASH")


def destroy_scenes(s: StashInterface, dry_run: bool, scene_list: List[Scene], delete: bool = False):
    log_start("DESTROY SCENES")
    log("Dry run: " + str(dry_run))
    log("Number of scenes to delete: " + str(len(scene_list)))
    for scene in scene_list:
        if not dry_run:
            for i in range(3):
                try:
                    s.destroy_scene(scene.id, delete)
                    log("DELETED SCENE %s" % scene.id)
                    break
                except Exception as e:
                    log("FAILED TO DELETE SCENE %s" % scene.id)
                    print(f"Received a GraphQL exception : {e}")
                    time.sleep(4)
        else:
            log("Scene to delete: " + str(scene.id))
    log_end("DESTROY SCENES")


if __name__ == "__main__":
    # TODO delete Shoko integration in an other class
    # TODO fix log timezone
    # TODO add a method to remove tag UNKOWN from all scenes

    stash, paths = initialize()

    parser = argparse.ArgumentParser(description='Manage Stash operations')
    parser.add_argument('--delete_duplicates_scenes', action='store_true', help='Delete duplicate scenes')
    parser.add_argument('--process_files', action='store_true', help='Process files')
    parser.add_argument('--scan', action='store_true', help='Scan')
    parser.add_argument('--test', action='store_true', help='Process test')
    args = parser.parse_args()

    if args.delete_duplicates_scenes:
        delete_duplicates_scenes(stash, PhashDistance.EXACT, False)
        delete_duplicates_scenes(stash, PhashDistance.HIGH, False)
        delete_duplicates_scenes(stash, PhashDistance.MEDIUM, False)
        delete_duplicates_scenes(stash, PhashDistance.LOW, False)
        delete_duplicates_files(stash, False)

    if args.process_files:
        process_corrupted(stash, SCENES_MAX, False)
        process_trash(stash, SCENES_MAX, paths, False)
        process_matches(stash, False)
        remove_matches(stash, False)
        remove_false_matches(stash, False)

    if args.scan:
        process_scan(stash)

    if args.test:
        process_test(stash, True)
