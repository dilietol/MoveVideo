from typing import Any

from stashapi.stashapp import StashInterface
from Log import Logger
from Types import Tags, Scene, SceneFilter
from FindBestFile import FileSlim

# Configuration constants used while paging through Stash scenes.
MATCHES_SCENES_MAX = 400
MATCHES_SCENES_PAGE = 200
MATCHES_SCENES_FALSE_POSITIVE_MAX = 800
MATCHES_SCENES_START_PAGE = 1
MATCHES_SCENES_INTERNAL_PAGE = 50


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

    ###### API ###########
    def find_scenes_by_filecount(self, scene_filter: SceneFilter,
                                 scenes_number_max) -> list[Scene]:
        # Build a Stash filter that selects scenes with more files than the configured threshold.
        scene_filter_str = {"organized": scene_filter.organized,
                            "file_count": {"value": scene_filter.file_count, "modifier": "GREATER_THAN"}
                            }
        scene_list = self.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)
        return scene_list

    ###### Stash wrapper ###########
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

    def make_primary_file(self, scene_id, primary_file_id):
        # Mark a file as the main one for the scene and log the operation.
        scene_id = self.stash_interface.update_scene({"id": scene_id, "primary_file_id": primary_file_id})
        self.logger.log(
            "File made primary: %s for scene: %s" % (str(primary_file_id), scene_id))

    def delete_file(self, file_id):
        # Remove the file from Stash and log the deletion for audit purposes.
        self.stash_interface.destroy_files([file_id])
        self.logger.log("File deleted: " + str(file_id))

    def scan(self):
        # Trigger a full metadata scan and record the operation in the logs.
        self.logger.log_start("PROCESS SCAN")
        self.stash_interface.metadata_scan()
        self.logger.log_end("PROCESS SCAN")
