import argparse
import concurrent.futures
import configparser
import json
import os
import time
from typing import List

from stashapi.stash_types import PhashDistance
from stashapi.stashapp import StashInterface

from Log import log, log_block, log_end, log_start
from Types import StashBox, Tags, Scene, SceneFilter, Studio, Performer, Match, Scrape
from FindBestFile import FileSlim, DuplicatedFiles

MATCHES_FALSE_POSITIVE = "MATCH_FALSE"  # Tag to add to scene when is not a match
MATCHES_FILTERED = ""  # Tag to use to filter scenes to process
MATCHES_DONE = "MATCH_DONE"  # Tag to add to scene when is processed
MATCHES_UNKNOWN = "UNKNOWN"  # Tag to add to scene when is unknown
MATCHES_SCENES_PAGE = 200
MATCHES_SCENES_MAX = 400
MATCHES_SCENES_START_PAGE = 1
MATCHES_SCENES_INTERNAL_PAGE = 50
SCENES_MAX = 1000

MATCHES_STASHBOX: List[StashBox] = [
    StashBox(name="stashdb.org", tag_name="MATCH_STASHDB", id=0, tag_id=0),
    StashBox(name="ThePornDB", tag_name="MATCH_PORNDB", id=0, tag_id=0),
    StashBox(name="FansDB", tag_name="MATCH_FANSDB", id=0, tag_id=0),
    StashBox(name="PMV Stash", tag_name="MATCH_PMV", id=0, tag_id=0)
]


def parse_config():
    conf = configparser.ConfigParser()
    defaults_path = os.path.join('config', 'config.toml')
    conf.read(defaults_path)
    return conf


def initialize() -> (StashInterface, dict, dict):
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
    return stash, config["Path"], config["Scenes"]


def get_scene_duplicated_files(distance: PhashDistance, s: StashInterface) -> list[DuplicatedFiles]:
    # TODO: StashCli
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
    # TODO: StashCli
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
    # TODO: StashCli
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
    # TODO: StashCli
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
    # TODO: StashCli
    LOG_INTERVAL = 10
    counter = 0
    for scene in scene_list:
        counter += 1
        if not dry_run:
            for i in range(3):
                try:
                    scene_id = s.update_scene({"id": scene.id, "tag_ids": ([tag.id for tag in scene.tags])})
                    log("UPDATED TAGs %s TO SCENE %s : %s" % (
                        ",".join([tag.name for tag in scene.tags]), scene_id, scene.title))
                    break
                except Exception as e:
                    log("FAILED TO UPDATE TAGS %s TO SCENE %s" % (",".join([tag.name for tag in scene.tags]), scene.id))
                    print(f"Received a GraphQL exception : {e}")
                    time.sleep(4)
        else:
            log("Tags to add: " + ",".join([tag.name for tag in scene.tags]) + " to scene: " + str(
                scene.id) + " : " + str(scene.title))
        if counter % LOG_INTERVAL == 0:
            log("UPDATED " + str(counter) + " SCENE of " + str(len(scene_list)) + "---------- " + str(counter))


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


def call_stash_api(new_scene, s: StashInterface, scene, stashbox) -> bool:
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
    # TODO: StashCli
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
                             filter={"per_page": page_dim, "page": page_number, "sort": "id", "direction": "DESC"},
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
    # TODO: StashCli
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
    # TODO: StashCli
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
    # TODO: StashCli
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
    # TODO: StashCli
    # Find scenes
    scene_filter_str = {"organized": scene_filter.organized,
                        "file_count": {"value": scene_filter.file_count, "modifier": "GREATER_THAN"}
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)
    return scene_list


def find_scenes_by_tags_path(s: StashInterface, tags_list: list[Tags], scene_filter: SceneFilter,
                             scenes_number_max) -> list[Scene]:
    # TODO: StashCli
    # TODO to fix path because is not working properly
    # Find scenes
    scene_filter_str = {"organized": scene_filter.organized,
                        "tags":
                            {"value": [tag.id for tag in tags_list if tag.name in scene_filter.tags_includes],
                             "excludes": [tag.id for tag in tags_list if tag.name in scene_filter.tags_excludes],
                             "modifier": "INCLUDES_ALL",
                             "depth": 0
                             },
                        "path": {"value": scene_filter.path, "modifier": "INCLUDES"}
                        }
    scene_list = find_scenes_by_scene_filter(s, scene_filter_str, scenes_number_max)
    return scene_list


def find_scenes_to_match(s: StashInterface, tags_list: list[Tags], stashbox_list: list[StashBox], scenes_number_max) -> \
        list[Scene]:
    # Find scenes
    scene_filter = SceneFilter(organized=False, tags_includes=[MATCHES_FILTERED],
                               tags_excludes=([x.tag_name for x in stashbox_list] + [MATCHES_FALSE_POSITIVE,
                                                                                     MATCHES_DONE]))
    scene_list = find_scenes_by_tags(s, tags_list, scene_filter, scenes_number_max)
    # log_block(scene_list, "FIND SCENES")
    return scene_list


def process_matches_old(s: StashInterface, dry_run=True):
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


def create_studio(s: StashInterface, stashbox: StashBox, studio: Studio) -> None:
    # TODO: StashCli
    executed = False
    try:

        s.create_studio(
            {"name": studio.name, "url": studio.url,
             "parent_id": studio.parent.get("stored_id") if studio.parent is not None else None,
             "image": studio.image,
             "stash_ids": [{"endpoint": stashbox.url, "stash_id": studio.remote_site_id}]})
        log("STUDIO CREATED: " + studio.name)
        executed = True
    except Exception as e:
        log("FAILED TO CREATE STUDIO: " + studio.name)
        log(f"Received a GraphQL exception : {e}")
    return executed


def create_performer(s: StashInterface, stashbox: StashBox, performer: Performer) -> bool:
    # TODO: StashCli
    executed = False
    try:
        result = s.create_performer(
            {"name": performer.name, "disambiguation": performer.disambiguation, "urls": performer.urls,
             "gender": performer.gender, "birthdate": performer.birthdate, "ethnicity": performer.ethnicity,
             "country": performer.country, "eye_color": performer.eye_color, "height_cm": performer.height,
             "measurements": performer.measurements, "fake_tits": performer.fake_tits,
             "penis_length": performer.penis_length, "circumcised": performer.circumcised,
             "career_length": performer.career_length, "tattoos": performer.tattoos,
             "piercings": performer.piercings,
             "alias_list": performer.aliases.split(",") if performer.aliases is not None else [],
             "favorite": False, "image": performer.images[0] if len(performer.images) > 0 else None,
             "details": performer.details, "death_date": performer.death_date,
             "hair_color": performer.hair_color, "weight": performer.weight,
             "stash_ids": [{"endpoint": stashbox.url, "stash_id": performer.remote_site_id}]})
        if result is not None:
            log("PERFORMER CREATED: " + performer.name)
            executed = True
        else:
            log("FAILED TO CREATE PERFORMER: " + performer.name)
    except Exception as e:
        log("FAILED TO CREATE PERFORMER: " + performer.name)
        log(f"Received a GraphQL exception : {e}")
    return executed


def update_scene(s: StashInterface, scrape: Scrape, match_index: int = 0) -> bool:
    # TODO: StashCli
    executed = False
    match: Match = scrape.matches[match_index]
    for i in range(5):
        try:
            s.update_scene({"id": scrape.scene.id, "title": scrape.matches[match_index].title, "code": match.code,
                            "details": match.details, "director": match.director, "urls": match.urls,
                            "date": match.date, "organized": True, "studio_id": match.studio.stored_id,
                            "performer_ids": [performer.stored_id for performer in match.performers],
                            "cover_image": match.image,
                            "stash_ids": [{"endpoint": scrape.stashbox.url, "stash_id": match.remote_site_id}]
                            })
            executed = True
            break
        except Exception as e:
            log("FAILED TO UPDATE SCENE %s FROM STASHBOX %s" % (scrape.scene.id, scrape.stashbox.name))
            log(f"Received a GraphQL exception : {e}")
            time.sleep(4)
    if executed:
        log("SCENE UPDATED: " + scrape.scene.id + " : " + scrape.matches[0].title)
    return executed


def find_update_scene_by_stashbox(s: StashInterface, stashbox: StashBox, tags_list, scenes_number_max=20,
                                  dry_run=True) -> \
        list[Scrape]:
    scene_filter = SceneFilter(organized=False, tags_includes=[stashbox.tag_name],
                               tags_excludes=([MATCHES_FALSE_POSITIVE]))
    scene_list = find_scenes_by_tags(s, tags_list, scene_filter, scenes_number_max)
    scrape_list = scrape_update_scene(s, scene_list, stashbox, dry_run)
    return scrape_list


def scrape_update_scene(s, scene_list, stashbox, dry_run=True) -> list[Scrape]:
    log_start("SCRAPE & UPDATE SCENE for stashbox: " + stashbox.name)
    # log_block(scene_list, "SCENES FOUND")
    LOG_INTERVAL = 10
    i = 0
    scrape_list: List[Scrape] = []
    for scene in scene_list:
        created: bool = False
        failed: bool = False
        i = i + 1
        scrape = Scrape(s, scene, stashbox)
        # log(stashbox.name + " : " + str(i) + " : " + str(scrape))
        if len(scrape.matches) == 0:
            log("No match found: " + scene.id + " for stashbox: " + stashbox.name)
        for match in scrape.matches:
            # log(stashbox.name + " : " + str(i) + " : " + str(match))
            for performer in match.performers:
                # log(stashbox.name + " : " + str(i) + " : " + str(performer))
                if performer.stored_id is None:
                    if dry_run is False:
                        result = create_performer(s, stashbox, performer)
                        if result is True:
                            created = True
                        else:
                            failed = True
                    else:
                        log("PERFORMER TO CREATE: " + performer.name)
            studio: Studio = match.studio
            # log(stashbox.name + " : " + str(i) + " : " + str(studio))
            if studio.stored_id is None:
                if dry_run is False:
                    created = created or create_studio(s, stashbox, studio)
                else:
                    log("STUDIO TO CREATE: " + studio.name)
        if created:
            scrape = Scrape(s, scene, stashbox)
        if scrape.scene.organized is False and failed is False:
            if scrape.calc_match is True:
                log(str(stashbox.name) + " Good match found: " + scrape.scene.id + " : " + str(scrape.matches[0].title))
                if dry_run is False:
                    update_scene(s, scrape)
                else:
                    log("SCENE TO UPDATE: " + scrape.scene.id + " : " + scrape.matches[0].title)
            else:
                log(str(stashbox.name) + " Bad match found: " + scrape.scene.id + " : " + str(
                    scrape.scene.files[0].basename))
        else:
            log(str(stashbox.name) + " Error match found: " + scrape.scene.id + " : " + str(scrape.matches[0].title))
        scrape_list.append(scrape)
        if i % LOG_INTERVAL == 0:
            log(stashbox.name + " : SCRAPED " + str(i) + " SCENE of " + str(
                len(scene_list)) + " ------------------- " + str(i))
    log_end("SCRAPE & UPDATE SCENE for stashbox: " + stashbox.name)
    return scrape_list


def get_scrape_scene(s: StashInterface, scene_list: List[Scene], stashbox: StashBox) -> list[Scrape]:
    # Get scrapes for scenes from stashbox
    # TODO: StashCli
    log_start("SCRAPE SCENE for stashbox: " + stashbox.name)
    # log_block(scene_list, "SCENES FOUND")
    LOG_INTERVAL = 20
    i = 0
    scrape_list: List[Scrape] = []
    for scene in scene_list:
        i = i + 1
        scrape = Scrape(s, scene, stashbox)
        # log(stashbox.name + " : " + str(i) + " : " + str(scrape))
        if len(scrape.matches) == 0:
            log(stashbox.name + " - No match found: " + scene.id)
        else:
            for match in scrape.matches:
                log(stashbox.name + " - Match found: " + scene.id + " : " + str(match.title))
        scrape_list.append(scrape)
        if i % LOG_INTERVAL == 0:
            log(stashbox.name + " : SCRAPED " + str(i) + " SCENE of " + str(len(scene_list)) + "----------" + str(i))
    log_end("SCRAPE SCENE for stashbox: " + stashbox.name)
    return scrape_list


def process_matches(s: StashInterface, scene_max_number: int = 3000, dry_run=True):
    # TODO: add a final report with the number of scenes matched
    log_start("PROCESS MATCHES")
    # Retrieve all tags from the StashInterface object
    tags_list: List[Tags] = get_tags(s)

    # log_block(tags_list, "TAGS LIST")
    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)
    # log_block(stashbox_list, "STASHBOX LIST")

    # Find scenes to match
    scene_list = find_scenes_to_match(s, tags_list, stashbox_list, scene_max_number)

    result: list[str, list[Scrape]] = list()
    result: list[Scrape] = list()
    for stashbox in filter(lambda x: x.tag_name in ["MATCH_STASHDB", "MATCH_PORNDB", "MATCH_FANSDB"],
                           stashbox_list):
        scrape_list = get_scrape_scene(s, scene_list, stashbox)
        result = result + scrape_list

    # log("SCRAPE LIST: " + str(result))

    for i in range(len(scene_list)):
        scene = scene_list[i]
        found = False
        tags: list[Tags] = scene.tags
        for scrape in result:
            if scene.id == scrape.scene.id and len(scrape.matches) > 0:
                found = True
                tags.append(Tags(id=scrape.stashbox.tag_id, name=scrape.stashbox.tag_name))
        if found is False:
            tags.extend([tag for tag in tags_list if tag.name == "MATCH_DONE"])
        scene_list[i].tags = tags
    update_tags(scene_list, s, dry_run)

    log_end("PROCESS MATCHES")


def process_update_scene_path(s: StashInterface, path: str, dry_run=True):
    log_start("PROCESS UPDATE SCENE PATH")
    log("Processing path: " + path)

    tags_list: List[Tags] = get_tags(s)
    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)

    for stashbox in filter(lambda x: x.tag_name in ["MATCH_STASHDB", "MATCH_PORNDB", "MATCH_FANSDB"],
                           stashbox_list):
        scene_filter = SceneFilter(organized=False, tags_includes=[stashbox.tag_name],
                                   tags_excludes=([MATCHES_FILTERED, MATCHES_FALSE_POSITIVE, MATCHES_DONE]),
                                   path=path)
        # log("Scene filter: " + str(scene_filter))
        scene_list = find_scenes_by_tags_path(s, tags_list, scene_filter, 168)

        # log_block(scene_list, "SCENES FOUND")

        scrape_list = scrape_update_scene(s, scene_list, stashbox, dry_run)
    log_end("PROCESS UPDATE SCENE PATH")


def process_update_scene_all(s: StashInterface, dry_run=True):
    # Scrape and updates all scenes selected by tag from all stashboxes.
    log_start("PROCESS UPDATE SCENE ALL")
    tags_list: List[Tags] = get_tags(s)
    # log_block(tags_list, "TAGS LIST")
    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)
    # log_block(stashbox_list, "STASHBOX LIST")

    result: list[Scrape] = list()
    for stashbox in filter(lambda x: x.tag_name in ["MATCH_STASHDB", "MATCH_PORNDB", "MATCH_FANSDB", "MATCH_PMV"],
                           stashbox_list):
        # TODO: modify scene_number to 400 when all is ok
        result = result + find_update_scene_by_stashbox(s, stashbox, tags_list, 2, dry_run=dry_run)
    log_end("PROCESS UPDATE SCENE ALL")


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
    scene_list = find_scenes_by_included_tags(s, tags_list, scene_filter, 2000)
    # log_block(scene_list, "FIND SCENES")

    remove_tags(scene_list, s, [x for x in tags_list if
                                x.name in [y.tag_name for y in stashbox_list] or x.name in [MATCHES_FALSE_POSITIVE,
                                                                                            MATCHES_DONE,
                                                                                            MATCHES_UNKNOWN]], dry_run)
    log_end("REMOVE MATCHES")


def remove_false_matches(s: StashInterface, dry_run=True):
    log_start("REMOVE FALSE MATCHES")
    tags_list: List[Tags] = get_tags(s)
    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)

    scene_filter = SceneFilter(organized=False,
                               tags_includes=[MATCHES_FALSE_POSITIVE],
                               tags_excludes=([]))
    scene_list = find_scenes_by_included_all_tags(s, tags_list, scene_filter, MATCHES_SCENES_MAX)

    # filter scenes with only false positives and unknown
    scene_list_filtered = []
    for elem in scene_list:
        if any(x.name not in [MATCHES_FALSE_POSITIVE, MATCHES_UNKNOWN] for x in elem.tags):
            scene_list_filtered.append(elem)
    scene_list = scene_list_filtered

    remove_tags(scene_list, s, [x for x in tags_list if
                                x.name in [y.tag_name for y in stashbox_list] or x.name in [MATCHES_DONE]], dry_run)

    log_end("REMOVE FALSE MATCHES")
    pass


def delete_duplicates_files(s: StashInterface, dry_run=True):
    # TODO: to fix because currently is not working properly
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


def process_reset_scene_path(s: StashInterface, path: str, reset_scene_max_number=500, dry_run=True):
    # remove tag MATCH_DONE from all scenes in a path
    log_start("PROCESS RESET SCENE PATH")
    tags_list: List[Tags] = get_tags(s)
    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)

    scene_filter = SceneFilter(organized=False, tags_includes=[MATCHES_DONE],
                               tags_excludes=([MATCHES_FILTERED, MATCHES_FALSE_POSITIVE]),
                               path=path)
    scene_list = find_scenes_by_tags_path(s, tags_list, scene_filter, reset_scene_max_number)
    remove_tags(scene_list, s, [x for x in tags_list if x.name in [MATCHES_DONE]], dry_run)
    log_end("PROCESS RESET SCENE PATH")


def process_test(s: StashInterface, dry_run=True):
    # TODO: Complete the test. Use this method to test new code and API call
    log_start("PROCESS Test")
    # Retrieve all tags from the StashInterface object
    tags_list: List[Tags] = get_tags(s)

    log_block(tags_list, "TAGS LIST")
    stashbox_list: List[StashBox] = get_stashbox_list(s, tags_list)
    log_block(stashbox_list, "STASHBOX LIST")

    scene_filter = SceneFilter(organized=False, tags_includes=[MATCHES_DONE],
                               tags_excludes=([MATCHES_FILTERED, MATCHES_FALSE_POSITIVE]),
                               path="/61.1_series/61.1.9.import/categories")
    scene_list = find_scenes_by_tags_path(s, tags_list, scene_filter, 30)

    remove_tags(scene_list, s, [x for x in tags_list if x.name in [MATCHES_DONE]], dry_run)
    log_end("PROCESS Test")


if __name__ == "__main__":
    # TODO move Shoko integration in an other class
    # TODO fix log timezone
    # TODO add a method to remove tag UNKOWN from all scenes

    stash, paths, scenes = initialize()

    parser = argparse.ArgumentParser(description='Manage Stash operations')
    parser.add_argument('--delete_duplicates_scenes', action='store_true',
                        help='Delete duplicate scenes using Stash functionalities')
    parser.add_argument('--delete_duplicates_files', action='store_true', help='Delete duplicate files using phash')
    parser.add_argument('--process_files', action='store_true', help='Process files for matches')
    parser.add_argument('--garbage', action='store_true', help='Process some garbage collection activities')
    parser.add_argument('--scan', action='store_true', help='Scan')
    parser.add_argument('--update_scene_all', action='store_true', help='Process update files in all path')
    parser.add_argument('--update_scene_path', action='store_true', help='Process update files in path')
    parser.add_argument('--reset_scene_path', action='store_true', help='Reset tag for files in path')
    parser.add_argument('--test', action='store_true', help='Process test')

    parser.add_argument('--path', nargs="+", type=str, help='Path to process')

    args = parser.parse_args()

    if args.delete_duplicates_scenes:
        delete_duplicates_scenes(stash, PhashDistance.EXACT, False)
        delete_duplicates_scenes(stash, PhashDistance.HIGH, False)
        # delete_duplicates_scenes(stash, PhashDistance.MEDIUM, False)
        # delete_duplicates_scenes(stash, PhashDistance.LOW, False)

    if args.delete_duplicates_files:
        delete_duplicates_files(stash, False)

    if args.process_files:
        queryMaxNumber = int(scenes["QueryMaxNumber"]) if scenes["QueryMaxNumber"].isdigit() else int(3000)
        process_matches(stash, queryMaxNumber, False)

    if args.garbage:
        process_corrupted(stash, SCENES_MAX, False)
        process_trash(stash, SCENES_MAX, paths, False)
        remove_matches(stash, False)
        remove_false_matches(stash, False)

    if args.scan:
        process_scan(stash)

    if args.update_scene_all:
        process_update_scene_all(stash, False)

    if args.update_scene_path:
        for x in args.path:
            process_update_scene_path(stash, path=x, dry_run=False)

    if args.reset_scene_path:
        for x in args.path:
            for y in range(1, 30):
                process_reset_scene_path(stash, path=x, reset_scene_max_number=400, dry_run=False)

    if args.test:
        process_test(stash, False)
