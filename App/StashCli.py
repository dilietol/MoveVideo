import time
from typing import Any, List

from requests.exceptions import ConnectionError, Timeout
from stashapi.stashapp import StashInterface
from stashapi.stash_types import PhashDistance
from App.Log import Logger
from App.Types import Tags, Scene, SceneFilter, StashBox, DuplicatedFiles, Scrape, Studio, Match, Performer, MATCHES_STASHBOX
from App.FindBestFile import FileSlim

# Configuration constants used while paging through Stash scenes.
MATCHES_SCENES_MAX = 400
MATCHES_SCENES_PAGE = 200
MATCHES_SCENES_FALSE_POSITIVE_MAX = 800
MATCHES_SCENES_START_PAGE = 1
MATCHES_SCENES_INTERNAL_PAGE = 50
LOG_INTERVAL = 10


class StashCli:
    """Small wrapper around the Stash API used to query and mutate scene data."""

    def __init__(self, stash_args: dict[Any, Any]):
        # Keep a direct reference to the Stash interface and a logger for traceability.
        self.stash_interface = StashInterface(stash_args)
        self.logger = Logger("StashCli")

###### Manipulate data ###########
    @staticmethod
    def extract_file_slim(item) -> list[FileSlim]:
        # Convert a scene payload into a compact list of file metadata used by matching logic.
        # TODO: manage multiple files more explicitly when the payload structure changes.
        file_slims: list[FileSlim] = []
        for i, file in enumerate(item.get("files", [])):
            phash = oshash = None
            for elem in file.get("fingerprints"):
                if elem.get("type") == "phash":
                    phash = elem.get("value")
                if elem.get("type") == "oshash":
                    oshash = elem.get("value")
            file_slims.append(FileSlim(id=item.get("id"), organized=item.get("organized"),
                                       id_file=file.get("id"),
                                       width=file.get("width"),
                                       height=file.get("height"),
                                       video_codec=file.get("video_codec"),
                                       size=file.get("size"),
                                       duration=file.get("duration"),
                                       basename=file.get("basename"),
                                       format=file.get("format"),
                                       oshash=oshash,
                                       phash=phash
                                       ))
        return file_slims


    ###### Stash wrapper ###########

    def scan(self):
        # Trigger a full metadata scan and record the operation in the logs.
        self.logger.log_start("PROCESS SCAN")
        self.stash_interface.metadata_scan()
        self.logger.log_end("PROCESS SCAN")

    def make_primary_file(self, scene_id, primary_file_id):
        # Mark a file as the main one for the scene and log the operation.
        scene_id = self.stash_interface.update_scene({"id": scene_id, "primary_file_id": primary_file_id})
        self.logger.log(
            "File made primary: %s for scene: %s" % (str(primary_file_id), scene_id))

    def delete_file(self, file_id):
        # Remove the file from Stash and log the deletion for audit purposes.
        self.stash_interface.destroy_files([file_id])
        self.logger.log("File deleted: " + str(file_id))

    def destroy_scenes(self, dry_run: bool, scene_id_list: list[int], delete: bool = False):
        # Delete scenes from Stash with retry logic and detailed logging.
        self.logger.log_start("DESTROY SCENES")
        self.logger.log("Dry run: " + str(dry_run))
        self.logger.log("Number of scenes to delete: " + str(len(scene_id_list)))
        for scene_id in scene_id_list:
            if not dry_run:
                for attempt in range(3):
                    try:
                        self.stash_interface.destroy_scene(scene_id, delete)
                        self.logger.log("DELETED SCENE %s" % scene_id)
                        break
                    except (ConnectionError, Timeout) as e:
                        self.logger.log("FAILED TO DELETE SCENE %s (attempt %d/3): %s" % (scene_id, attempt + 1, str(e)))
                        if attempt < 2:
                            time.sleep(4)
                        else:
                            self.logger.log("Max retries reached for scene %s" % scene_id)
                    except Exception as e:
                        self.logger.log("Non-recoverable error deleting scene %s: %s" % (scene_id, str(e)))
                        self.logger.debug("Exception details:", exc_info=True)
                        break
            else:
                self.logger.log("Scene to delete: " + str(scene_id))
        self.logger.log_end("DESTROY SCENES")

    def get_tags(self, name: str = "") -> list[Tags]:
        # Retrieve tags from Stash, optionally filtered by name.
        result = list()
        data = self.stash_interface.find_tags()
        for elem in data:
            if elem["name"] == name or name == "":
                result.append(Tags(id=elem["id"], name=elem["name"]))
        return result

    def get_stashbox_list(self, tags_list: list[Tags]) -> list[StashBox]:
        # Retrieve and configure stashbox connections.
        stashbox_list: List[StashBox] = MATCHES_STASHBOX
        for stashbox in stashbox_list:
            for tag in tags_list:
                if stashbox.tag_name == tag.name:
                    stashbox.tag_id = tag.id
        stashbox_connections = self.stash_interface.get_stashbox_connections()
        for elem in stashbox_connections:
            data = self.stash_interface.get_stashbox_connection(elem["endpoint"])
            elem["id"] = data["index"]
            elem["url"] = elem["endpoint"]
        for stashbox in stashbox_list:
            for conn in stashbox_connections:
                if stashbox.name == conn.get("name"):
                    stashbox.id = conn.get("id")
                    stashbox.url = conn.get("url")
        return stashbox_list

    def create_performer(self, stashbox: StashBox, performer: Performer) -> bool:
        # TODO: StashCli
        executed = False
        try:
            result = self.stash_interface.create_performer(
                {"name": performer.name, "disambiguation": performer.disambiguation, "urls": performer.urls,
                 "gender": performer.gender, "birthdate": performer.birthdate, "ethnicity": performer.ethnicity,
                 "country": performer.country, "eye_color": performer.eye_color, "height_cm": performer.height,
                 "measurements": performer.measurements, "fake_tits": performer.fake_tits,
                 "penis_length": performer.penis_length, "circumcised": performer.circumcised, "tattoos": performer.tattoos,
                 "piercings": performer.piercings,
                 "alias_list": performer.aliases.split(",") if performer.aliases is not None else [],
                 "favorite": False, "image": performer.images[0] if len(performer.images) > 0 else None,
                 "details": performer.details, "death_date": performer.death_date,
                 "hair_color": performer.hair_color, "weight": performer.weight,
                 "stash_ids": [{"endpoint": stashbox.url, "stash_id": performer.remote_site_id}]})
            if result is not None:
                self.logger.log("PERFORMER CREATED: " + performer.name)
                executed = True
        except (ConnectionError, Timeout) as e:
            self.logger.log("FAILED TO CREATE PERFORMER %s (network error): %s" % (performer.name, str(e)))
        except Exception as e:
            self.logger.log("FAILED TO CREATE PERFORMER %s: %s" % (performer.name, str(e)))
            self.logger.debug("Exception details:", exc_info=True)
        return executed

    def create_studio(self, stashbox: StashBox, studio: Studio) -> bool:
        # TODO: StashCli
        executed: bool = False
        try:
            self.stash_interface.create_studio(
                {"name": studio.name, "urls": studio.urls,
                 "parent_id": studio.parent.get("stored_id") if studio.parent is not None else None,
                 "image": studio.image,
                 "stash_ids": [{"endpoint": stashbox.url, "stash_id": studio.remote_site_id}]})
            self.logger.log("STUDIO CREATED: " + studio.name)
            executed = True
        except (ConnectionError, Timeout) as e:
            self.logger.log("FAILED TO CREATE STUDIO %s (network error): %s" % (studio.name, str(e)))
        except Exception as e:
            self.logger.log("FAILED TO CREATE STUDIO %s: %s" % (studio.name, str(e)))
            self.logger.debug("Exception details:", exc_info=True)
        return executed




    def find_scenes_by_scene_filter(self, scene_filter_str, scenes_number_max=0) -> list[Scene]:
        # Fetch scenes page by page until the requested number of results is reached or the API returns no more data.
        scene_list = list()
        others = True
        page_number = MATCHES_SCENES_START_PAGE
        page_dim = MATCHES_SCENES_PAGE
        self.logger.log_start("FETCHING SCENES")
        while others:
            if scenes_number_max == 0:
                page_dim = MATCHES_SCENES_PAGE
            elif (scenes_number_max - len(scene_list)) < MATCHES_SCENES_PAGE:
                page_dim = scenes_number_max - len(scene_list)
            self.logger.log("Fetching page number " + str(page_number))
            data = self.stash_interface.find_scenes(f=scene_filter_str,
                                 filter={"per_page": page_dim, "page": page_number, "sort": "id", "direction": "DESC"},
                                 get_count=False)
            # log_block(data, "Data")
            for elem in data:
                scene_list.append(Scene(id=elem["id"], organized=elem["organized"], title=elem["title"],
                                        tags=[Tags(id=tag["id"], name=tag["name"]) for tag in elem["tags"]],
                                        files=self.extract_file_slim(elem)))
            page_number += 1
            if len(scene_list) >= scenes_number_max != 0:
                others = False
            if data is None or len(data) == 0 or len(data) < page_dim:
                others = False
        self.logger.log("Total fetched pages are " + str(page_number - 1) + " for " + str(len(scene_list)) + " scenes")
        self.logger.log_end("FETCHING SCENES")
        return scene_list

    def update_scene(self, scrape: Scrape, match: Match|None = None) -> bool:
        # TODO: StashCli
        executed = False
        if match is None:
            match: Match = scrape.matches[0]
        for attempt in range(5):
            try:
                self.stash_interface.update_scene({"id": scrape.scene.id, "title": match.title, "code": match.code,
                                "details": match.details, "director": match.director, "urls": match.urls,
                                "date": match.date, "organized": True, "studio_id": match.studio.stored_id,
                                "performer_ids": [performer.stored_id for performer in match.performers],
                                "cover_image": match.image,
                                "stash_ids": [{"endpoint": scrape.stashbox.url, "stash_id": match.remote_site_id}]
                                })
                executed = True
                break
            except (ConnectionError, Timeout) as e:
                self.logger.log("FAILED TO UPDATE SCENE %s FROM STASHBOX %s (attempt %d/5): %s" % (scrape.scene.id, scrape.stashbox.name, attempt + 1, str(e)))
                if attempt < 4:
                    time.sleep(4)
                else:
                    self.logger.log("Max retries reached for scene %s" % scrape.scene.id)
            except Exception as e:
                self.logger.log("Non-recoverable error updating scene %s: %s" % (scrape.scene.id, str(e)))
                self.logger.debug("Exception details:", exc_info=True)
                break
        if executed:
            self.logger.log("SCENE UPDATED: " + str(scrape.scene.id) + " : " + match.title)
        return executed

    def update_tags(self, scene_list: List[Scene], dry_run=True):
        """
        Update tags for scenes with retry logic.
        Args:
            scene_list: List of Scene objects to update.
            dry_run: If True, only log what would be updated without making changes.
        """
        counter = 0
        for scene in scene_list:
            counter += 1
            if not dry_run:
                for attempt in range(3):
                    try:
                        scene_id = self.stash_interface.update_scene({"id": scene.id, "tag_ids": ([tag.id for tag in scene.tags])})
                        self.logger.log("UPDATED TAGs %s TO SCENE %s : %s" % (
                            ",".join([tag.name for tag in scene.tags]), scene_id, scene.title))
                        break
                    except (ConnectionError, Timeout) as e:
                        self.logger.log("FAILED TO UPDATE TAGS %s TO SCENE %s (attempt %d/3): %s" % (
                            ",".join([tag.name for tag in scene.tags]), scene.id, attempt + 1, str(e)))
                        if attempt < 2:
                            time.sleep(4)
                        else:
                            self.logger.log("Max retries reached for scene %s" % scene.id)
                    except Exception as e:
                        self.logger.log("Non-recoverable error updating tags %s for scene %s" % (",".join([tag.name for tag in scene.tags]),scene.id))
                        self.logger.debug("Exception details: %s" % str(e), exc_info=True)
                        break
            else:
                self.logger.log("Tags to add: " + ",".join([tag.name for tag in scene.tags]) + " to scene: " + str(
                    scene.id) + " : " + str(scene.title))
            if counter % LOG_INTERVAL == 0:
                self.logger.log(
                    "UPDATED " + str(counter) + " SCENE of " + str(len(scene_list)) + "---------- " + str(counter))

    def remove_tags(self, scene_list: List[Scene], tag_list: List[Tags], dry_run=True):
        """
        Remove specified tags from scenes.
        Args:
            scene_list: List of Scene objects to process.
            tag_list: List of Tag objects to remove from scenes.
            dry_run: If True, only log what would be updated without making changes.
        """
        for scene in scene_list:
            for tag_elem in tag_list:
                if tag_elem.name in [x.name for x in scene.tags]:
                    scene.tags.remove(tag_elem)
        self.update_tags(scene_list, dry_run)

    def get_scene_duplicated_files(self, distance: PhashDistance) -> list[DuplicatedFiles]:
        """
        Find duplicate scenes based on phash distance.
        Args:
            distance: PhashDistance enum value for matching threshold.
        Returns:
            List of DuplicatedFiles objects containing duplicate scene information.
        """
        self.logger.log("DUPLICATE SCENES FOUND REQUEST")
        data = self.stash_interface.find_duplicate_scenes(distance=distance, fragment='...Scene')
        self.logger.log("DUPLICATE SCENES FOUND RESPONSE")
        compared_files_list: list[DuplicatedFiles] = []
        for element in data:
            duplicated_files_slim: list[FileSlim] = list()
            for item in element:
                file_slim = self.extract_file_slim(item)
                duplicated_files_slim.append(file_slim[0])
            compared_files_list.append(DuplicatedFiles(files=duplicated_files_slim))
        return compared_files_list


    ###### API ###########

    def find_scenes_by_filecount(self, scene_filter: SceneFilter,
                                 scenes_number_max) -> list[Scene]:
        # Build a Stash filter that selects scenes with more files than the configured threshold.
        scene_filter_str = {"organized": scene_filter.organized,
                            "file_count": {"value": scene_filter.file_count, "modifier": "GREATER_THAN"}
                            }
        scene_list = self.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)
        return scene_list

    def find_scenes_by_tags(self, tags_list: list[Tags], scene_filter: SceneFilter,
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
        scene_list = self.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)
        return scene_list

    def find_scenes_by_included_tags(self, tags_list: list[Tags], scene_filter: SceneFilter,
                                     scenes_number_max) -> list[Scene]:
        """
        Find scenes with included tags using INCLUDES modifier.
        Args:
            tags_list: List of tags to filter by.
            scene_filter: SceneFilter object with organized status and tags_includes.
            scenes_number_max: Maximum number of scenes to retrieve.
        Returns:
            List of Scene objects matching the filter criteria.
        """
        scene_filter_str = {"organized": scene_filter.organized,
                            "tags":
                                {"value": [tag.id for tag in tags_list if tag.name in scene_filter.tags_includes],
                                 "modifier": "INCLUDES",
                                 "depth": 0
                                 }
                            }
        scene_list = self.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)
        return scene_list

    def find_scenes_by_included_all_tags(self, tags_list: list[Tags], scene_filter: SceneFilter,
                                         scenes_number_max) -> list[Scene]:
        """
        Find scenes with all included tags using INCLUDES_ALL modifier.
        Args:
            tags_list: List of tags to filter by.
            scene_filter: SceneFilter object with organized status and tags_includes.
            scenes_number_max: Maximum number of scenes to retrieve.
        Returns:
            List of Scene objects matching the filter criteria.
        """
        scene_filter_str = {"organized": scene_filter.organized,
                            "tags":
                                {"value": [tag.id for tag in tags_list if tag.name in scene_filter.tags_includes],
                                 "modifier": "INCLUDES_ALL",
                                 "depth": 0
                                 }
                            }
        scene_list = self.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)
        return scene_list

    def find_scenes_by_tags_path(self, tags_list: list[Tags], scene_filter: SceneFilter,
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
        scene_list = self.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)
        return scene_list

    def get_scrape_scene(self, scene_list: List[Scene], stashbox: StashBox) -> list[Scrape]:
        # Get scrapes for scenes from stashbox
        # TODO: StashCli
        self.logger.log_start("SCRAPE SCENE for stashbox: " + stashbox.name)
        # log_block(scene_list, "SCENES FOUND")
        i = 0
        scrape_list: List[Scrape] = []
        for scene in scene_list:
            i = i + 1
            scrape = Scrape(self.stash_interface, scene, stashbox)
            # log(stashbox.name + " : " + str(i) + " : " + str(scrape))
            if len(scrape.matches) == 0:
                self.logger.log(stashbox.name + " - No match found: " + str(scene.id))
            else:
                for match in scrape.matches:
                    self.logger.log(stashbox.name + " - Match found: " + str(scene.id) + " : " + str(match.title))
            scrape_list.append(scrape)
            if i % LOG_INTERVAL == 0:
                self.logger.log(
                    stashbox.name + " : SCRAPED " + str(i) + " SCENE of " + str(len(scene_list)) + "----------" + str(
                        i))
        self.logger.log_end("SCRAPE SCENE for stashbox: " + stashbox.name)
        return scrape_list


    def scrape_update_scene(self, scene_list: List[Scene], stashbox: StashBox, dry_run: bool = True) -> list[Scrape]:
        self.logger.log_start("SCRAPE & UPDATE SCENE for stashbox: " + stashbox.name)
        # log_block(scene_list, "SCENES FOUND")
        i = 0
        scrape_list: List[Scrape] = []
        for scene in scene_list:
            created: bool = False
            failed: bool = False
            i = i + 1
            scrape = Scrape(self.stash_interface, scene, stashbox)
            # log(stashbox.name + " : " + str(i) + " : " + str(scrape))
            if len(scrape.matches) == 0:
                self.logger.log("No match found: " + str(scene.id) + " for stashbox: " + stashbox.name)
            for match in scrape.matches:
                # log(stashbox.name + " : " + str(i) + " : " + str(match))
                for performer in match.performers:
                    # log(stashbox.name + " : " + str(i) + " : " + str(performer))
                    if performer.stored_id is None:
                        if not dry_run:
                            result = self.create_performer(stashbox, performer)
                            if result:
                                created = True
                            else:
                                failed = True
                        else:
                            self.logger.log("PERFORMER TO CREATE: " + performer.name)
                studio: Studio = match.studio
                # log(stashbox.name + " : " + str(i) + " : " + str(studio))
                if studio.stored_id is None:
                    if not dry_run:
                        created = created or self.create_studio(stashbox, studio)
                    else:
                        self.logger.log("STUDIO TO CREATE: " + studio.name)
            if created:
                scrape = Scrape(self.stash_interface, scene, stashbox)
            if scrape.scene.organized is False and failed is False:
                if scrape.match:
                    self.logger.log(str(stashbox.name) + " Good match found: " + str(scrape.scene.id) + " : " + str(
                        scrape.match_object.title))
                    if scrape.index == 1:
                        # More than a match found
                        if not dry_run:
                            self.update_scene( scrape, scrape.match_object)
                        else:
                            self.logger.log("SCENE TO UPDATE: " + str(scrape.scene.id) + " : " + scrape.match_object.title)
                    else:
                        # Just one match
                        if not dry_run:
                            self.update_scene( scrape)
                        else:
                            self.logger.log("SCENE TO UPDATE: " + str(scrape.scene.id) + " : " + scrape.matches[0].title)
                else:
                    self.logger.log(str(stashbox.name) + " Bad match found: " + str(scrape.scene.id) + " : " + str(
                        scrape.scene.files[0].basename) + " : " + scrape.match_why)
            else:
                self.logger.log(str(stashbox.name) + " Error match found: " + str(scrape.scene.id) + " : " + str(
                    scrape.matches[0].title))
            scrape_list.append(scrape)
            if i % LOG_INTERVAL == 0:
                self.logger.log(stashbox.name + " : SCRAPED " + str(i) + " SCENE of " + str(
                    len(scene_list)) + " ------------------- " + str(i))
        self.logger.log_end("SCRAPE & UPDATE SCENE for stashbox: " + stashbox.name)
        return scrape_list