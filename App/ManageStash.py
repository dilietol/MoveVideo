import argparse
import concurrent.futures
import json
import os
import time
from typing import List
import toml

from stashapi.stash_types import PhashDistance
from stashapi.stashapp import StashInterface
from requests.exceptions import ConnectionError, Timeout

from Config import apply_env_overrides
from Log import Logger
from Types import StashBox, Tags, Scene, SceneFilter, Scrape
from FindBestFile import FileSlim, DuplicatedFiles
from StashCli import StashCli

MATCHES_FALSE_POSITIVE = "MATCH_FALSE"  # Tag to add to scene when is not a match
MATCHES_FILTERED = ""  # Tag to use to filter scenes to process
MATCHES_DONE = "MATCH_DONE"  # Tag to add to scene when is processed
MATCHES_UNKNOWN = "UNKNOWN"  # Tag to add to scene when is unknown
SCENES_MAX = 1000
MATCHES_SCENES_MAX = 400
MATCHES_SCENES_FALSE_POSITIVE_MAX = 800

MATCHES_STASHBOX: List[StashBox] = [
    StashBox(name="stashdb.org", tag_name="MATCH_STASHDB", id=0, tag_id=0),
    StashBox(name="ThePornDB", tag_name="MATCH_PORNDB", id=0, tag_id=0),
    StashBox(name="FansDB", tag_name="MATCH_FANSDB", id=0, tag_id=0),
    StashBox(name="PMV Stash", tag_name="MATCH_PMV", id=0, tag_id=0)
]


class ManageStash:
    def __init__(self):
        self.conf = None
        self.stash: StashCli
        self.paths = None
        self.query_max_number:int = 3000
        self.logger = Logger("ManageStash")
        self.initialize()

    def parse_config(self):
        defaults_path = None
        try:
            defaults_path = os.path.join('config', 'config.toml')
            with open(defaults_path, 'r') as f:
                self.conf = apply_env_overrides(toml.load(f))
        except FileNotFoundError:
            self.logger.log(f"Config file not found: {defaults_path}")
            raise
        except toml.TomlDecodeError as e:
            self.logger.log(f"Invalid TOML in config file: {e}")
            raise

    def initialize(self) -> None:
        # TODO reorganize stash interface in order to move this initialization in a package/file in the future and move there all the method that use stash interface; leaving in this file only the processing methods.
        self.parse_config()
        # Set up Stash
        stash_args = {
            "scheme": self.conf["Stash_Host"]["Scheme"],
            "host": self.conf["Stash_Host"]["Host"],
            "port": self.conf["Stash_Host"]["Port"]
        }
        if self.conf["Stash_Host"].get("ApiKey"):
            stash_args["ApiKey"] = self.conf["Stash_Host"]["ApiKey"]
        self.stash = StashCli(stash_args)
        self.paths = self.conf["Path"]
        scenes = self.conf["Scenes"]
        try:
            if scenes.get("QueryMaxNumber"):
                self.query_max_number = int(scenes.get("QueryMaxNumber"))
        except (KeyError, ValueError) as e:
            self.logger.error(f"Invalid QueryMaxNumber configuration: {e}")
            raise

        return

    def get_scene_duplicated_files(self, distance: PhashDistance, s: StashInterface) -> list[DuplicatedFiles]:
        # TODO: StashCli
        self.logger.log("DUPLICATE SCENES FOUND REQUEST")
        data = s.find_duplicate_scenes(distance=distance, fragment='...Scene')
        self.logger.log("DUPLICATE SCENES FOUND RESPONSE")
        # log_block(data, "DUPLICATE SCENES DETAILS")
        compared_files_list: list[DuplicatedFiles] = []
        for element in data:
            duplicated_files_slim: list[FileSlim] = list()
            for item in element:
                file_slim = self.stash.extract_file_slim(item)
                duplicated_files_slim.append(file_slim[0])
            compared_files_list.append(DuplicatedFiles(files=duplicated_files_slim))
        return compared_files_list

    def delete_duplicates_scenes(self, p: PhashDistance = PhashDistance.EXACT, dry_run=True):
        self.logger.log_start("DELETE DUPLICATES SCENES")
        self.logger.log("Parameters: Distance %s - DryRun %s" % (p.name, dry_run))
        compared_files_list = self.stash.get_scene_duplicated_files(p)
        # log_block(compared_files_list, "COMPARED FILES")

        deleted_size_sum = 0
        deleted_scenes_id_list: list[int] = []
        counters = {}
        counters_ok = {}
        for elem in compared_files_list:
            if elem.id != 0:
                deleted_size_sum += elem.to_delete_size
                deleted_scenes_id_list.extend(elem.to_delete)
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
        for array in compared_files_list:
            array_of_files.extend(array.files)

        self.logger.log("Dry run: " + str(dry_run))
        self.logger.log("Number of comparison: " + str(len(compared_files_list)))
        self.logger.log("Number of compared files: " + str(len(array_of_files)))
        self.logger.log("Size to delete: " + str(deleted_size_sum))
        self.logger.log("Number of files to delete: " + str(len(deleted_scenes_id_list)))
        self.logger.log("counters for valid duplicates: " + json.dumps(counters_ok))
        self.logger.log("counters for not valid duplicates: " + json.dumps(counters))

        # TODO refactor in order to use the destroy_scenes method
        self.stash.destroy_scenes(dry_run, deleted_scenes_id_list, True)
        self.logger.log_end("DELETE DUPLICATES SCENES")

    def find_scene_matches(self, s, scene_list: List[Scene], stashbox_list: List[StashBox], tag_list: List[Tags]) -> \
            List[
                Scene]:
        # Scrape scenes
        scenes_counter = 0
        result: List[Scene] = list()
        self.logger.log_start("FETCHING SCENE MATCHES")
        for scene in scene_list:
            new_scene = Scene(id=scene.id, organized=scene.organized, tags=scene.tags, files=list())
            scenes_counter += 1
            if scenes_counter % 10 == 0:
                self.logger.log("Scenes processed: " + str(scenes_counter))
            found = False
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.call_stash_api, new_scene, s, scene, stashbox) for stashbox in
                           stashbox_list]
                for future in concurrent.futures.as_completed(futures):
                    found = found or future.result()
            if not found:
                self.logger.log("Scene %s NOT found" % scene.id)
                new_scene.tags.extend([tag for tag in tag_list if
                                       tag.name == MATCHES_DONE])
            result.append(new_scene)
        self.logger.log_end("FETCHING SCENE MATCHES")
        return result

    def call_stash_api(self, new_scene, s: StashInterface, scene, stashbox) -> bool:
        data = None
        found = False
        for attempt in range(3):
            try:
                data = s.scrape_scene({"stash_box_endpoint": stashbox.url}, {"scene_id": scene.id})
                break
            except (ConnectionError, Timeout) as e:
                self.logger.log("FAILED TO SCRAPE SCENE %s FROM STASHBOX %s (attempt %d/3): %s" % (scene.id, stashbox.name, attempt + 1, str(e)))
                if attempt < 2:
                    time.sleep(4)
                else:
                    self.logger.log("Max retries reached for scene %s from %s" % (scene.id, stashbox.name))
            except Exception as e:
                self.logger.log("Non-recoverable error scraping scene %s from %s: %s" % (scene.id, stashbox.name, str(e)))
                self.logger.debug("Exception details:", exc_info=True)
                break
        if data is not None:
            self.logger.log("Scene %s found in %s" % (scene.id, stashbox.name))
            new_scene.tags.append(Tags(id=stashbox.tag_id, name=stashbox.tag_name))
            found = True
        return found

    def find_scenes_to_match(self,tags_list: list[Tags], stashbox_list: list[StashBox],
                             scenes_number_max) -> \
            list[Scene]:
        # Find scenes
        scene_filter = SceneFilter(organized=False, tags_includes=[MATCHES_FILTERED],
                                   tags_excludes=([x.tag_name for x in stashbox_list] + [MATCHES_FALSE_POSITIVE,
                                                                                         MATCHES_DONE]))
        scene_list = self.stash.find_scenes_by_tags(tags_list, scene_filter, scenes_number_max)
        # log_block(scene_list, "FIND SCENES")
        return scene_list

    def find_update_scene_by_stashbox(self, stashbox: StashBox, tags_list, scenes_number_max=20,
                                      dry_run=True) -> \
            list[Scrape]:
        scene_filter = SceneFilter(organized=False, tags_includes=[stashbox.tag_name],
                                   tags_excludes=([MATCHES_FALSE_POSITIVE]))
        scene_list = self.stash.find_scenes_by_tags(tags_list, scene_filter, scenes_number_max)
        scrape_list = self.stash.scrape_update_scene(scene_list, stashbox, dry_run)
        return scrape_list

    def process_matches(self, scene_max_number: int = 3000, dry_run=True):
        # TODO: add a final report with the number of scenes matched
        self.logger.log_start("PROCESS MATCHES")
        self.logger.log("Processing scenes with max scenes: " + str(scene_max_number) + " (dry run: " + str(dry_run) + ")")
        # Retrieve all tags from Stash
        tags_list: List[Tags] = self.stash.get_tags()

        # log_block(tags_list, "TAGS LIST")
        stashbox_list: List[StashBox] = self.stash.get_stashbox_list(tags_list)
        # log_block(stashbox_list, "STASHBOX LIST")

        # Find scenes to match
        scene_list = self.find_scenes_to_match(tags_list, stashbox_list, scene_max_number)

        result: list[Scrape] = []
        # Filter stashboxes to process
        stashboxes_to_process = [sb for sb in stashbox_list if sb.tag_name in ["MATCH_STASHDB", "MATCH_PORNDB"]]
        
        # Process stashboxes in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit all tasks
            future_to_stashbox = {
                executor.submit(self.stash.get_scrape_scene, scene_list, stashbox): stashbox
                for stashbox in stashboxes_to_process
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_stashbox):
                stashbox = future_to_stashbox[future]
                try:
                    scrape_list = future.result()
                    result.extend(scrape_list)
                except Exception as exc:
                    self.logger.log(f"{stashbox.name} generated an exception: {exc}")

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
        self.stash.update_tags(scene_list, dry_run)

        self.logger.log_end("PROCESS MATCHES")

    def process_update_scene_path(self, path: str, dry_run=True):
        self.logger.log_start("PROCESS UPDATE SCENE PATH")
        self.logger.log("Processing path: " + path + " (dry run: " + str(dry_run) + ")")

        tags_list: List[Tags] = self.stash.get_tags()
        stashbox_list: List[StashBox] = self.stash.get_stashbox_list(tags_list)

        for stashbox in filter(lambda x: x.tag_name in ["MATCH_STASHDB", "MATCH_PORNDB"],
                               stashbox_list):
            scene_filter = SceneFilter(organized=False, tags_includes=[stashbox.tag_name],
                                       tags_excludes=([MATCHES_FILTERED, MATCHES_FALSE_POSITIVE, MATCHES_DONE]),
                                       path=path)
            # log("Scene filter: " + str(scene_filter))
            scene_list = self.stash.find_scenes_by_tags_path(tags_list, scene_filter, 400)

            # log_block(scene_list, "SCENES FOUND")

            self.stash.scrape_update_scene(scene_list, stashbox, dry_run)
        self.logger.log_end("PROCESS UPDATE SCENE PATH")

    def process_update_scene_all(self, dry_run=True):
        # Scrape and updates all scenes selected by tag from all stashboxes.
        self.logger.log_start("PROCESS UPDATE SCENE ALL")
        tags_list: List[Tags] = self.stash.get_tags()
        # log_block(tags_list, "TAGS LIST")
        stashbox_list: List[StashBox] = self.stash.get_stashbox_list(tags_list)
        # log_block(stashbox_list, "STASHBOX LIST")

        result: list[Scrape] = list()
        for stashbox in filter(lambda x: x.tag_name in ["MATCH_STASHDB", "MATCH_PORNDB"],
                               stashbox_list):
            # TODO: modify scene_number to 400 when all is ok
            result = result + self.find_update_scene_by_stashbox(stashbox, tags_list, 2, dry_run=dry_run)
        self.logger.log_end("PROCESS UPDATE SCENE ALL")

    def remove_matches(self, dry_run=True):
        """
        Remove match-related tags from organized scenes.
        Removes tags for stashbox matches, false positives, done status, and unknown status
        from scenes that are marked as organized.
        Args:
            dry_run: If True, only log what would be updated without making changes.
        """
        self.logger.log_start("REMOVE MATCHES")
        # Retrieve all tags from Stash
        tags_list: List[Tags] = self.stash.get_tags()
        # log_block(tags_list, "TAGS LIST")

        stashbox_list: List[StashBox] = self.stash.get_stashbox_list(tags_list)
        # log_block(stashbox_list, "STASHBOX LIST")

        scene_filter = SceneFilter(organized=True,
                                   tags_includes=[MATCHES_FILTERED] + [x.tag_name for x in stashbox_list] + [
                                       MATCHES_FALSE_POSITIVE, MATCHES_DONE, MATCHES_UNKNOWN],
                                   tags_excludes=([]))
        scene_list = self.stash.find_scenes_by_included_tags(tags_list, scene_filter, 2000)
        # log_block(scene_list, "FIND SCENES")

        self.stash.remove_tags(scene_list, [x for x in tags_list if
                                         x.name in [y.tag_name for y in stashbox_list] or x.name in [
                                             MATCHES_FALSE_POSITIVE,
                                             MATCHES_DONE,
                                             MATCHES_UNKNOWN]],
                         dry_run)
        self.logger.log_end("REMOVE MATCHES")

    def remove_false_matches(self, dry_run=True):
        """
        Clean up false positive matches while preserving valid matches.
        Removes stashbox match tags from scenes that have only false positives and unknown tags,
        keeping only the MATCH_DONE tag for clean scenes.
        Args:
            dry_run: If True, only log what would be updated without making changes.
        """
        self.logger.log_start("REMOVE FALSE MATCHES")
        tags_list: List[Tags] = self.stash.get_tags()
        stashbox_list: List[StashBox] = self.stash.get_stashbox_list(tags_list)

        scene_filter = SceneFilter(organized=False,
                                   tags_includes=[MATCHES_FALSE_POSITIVE],
                                   tags_excludes=([]))
        scene_list = self.stash.find_scenes_by_included_all_tags(tags_list, scene_filter, MATCHES_SCENES_FALSE_POSITIVE_MAX)

        # filter scenes with only false positives and unknown
        scene_list_filtered = []
        for elem in scene_list:
            if any(x.name in [y.tag_name for y in stashbox_list] or x.name in [MATCHES_DONE] for x in elem.tags):
                scene_list_filtered.append(elem)
        scene_list = scene_list_filtered
        self.logger.log("Number of scenes with tags to remove: " + str(len(scene_list)))

        self.stash.remove_tags(scene_list, [x for x in tags_list if
                                         x.name in [y.tag_name for y in stashbox_list] or x.name in [MATCHES_DONE]],
                         dry_run)

        self.logger.log_end("REMOVE FALSE MATCHES")
        pass

    def delete_duplicates_files(self, dry_run=True):
        self.logger.log_start("DELETE DUPLICATES FILES")
        scene_filter = SceneFilter(organized=True, file_count=1, tags_includes=[],
                                   tags_excludes=[])
        scene_list = self.stash.find_scenes_by_filecount(scene_filter, MATCHES_SCENES_MAX)
        # log_block(scene_list, "FIND SCENES")

        deleted_size_sum = 0
        deleted_files_id_list: list[int] = []
        counters = {}
        counters_ok = {}
        for elem in scene_list:
            self.logger.log("Processing scene: " + str(elem.title) + " (id: " + str(elem.id) + ")")
            if elem.duplicated_files.id_file != 0:
                deleted_size_sum += elem.duplicated_files.to_delete_size
                deleted_files_id_list.extend(elem.duplicated_files.to_delete_files)
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
        for array in scene_list:
            array_of_files.extend(array.duplicated_files.files)

        self.logger.log("Dry run: " + str(dry_run))
        self.logger.log("Number of comparison: " + str(len(scene_list)))
        self.logger.log("Number of compared files: " + str(len(array_of_files)))
        self.logger.log("Size to delete: " + str(deleted_size_sum))
        self.logger.log("Number of files to delete: " + str(len(deleted_files_id_list)))
        self.logger.log("counters for valid duplicates: " + json.dumps(counters_ok))
        self.logger.log("counters for not valid duplicates: " + json.dumps(counters))

        for scene in scene_list:
            if scene.duplicated_files.id_file != 0:
                if not dry_run:
                    if scene.duplicated_files.id_file != scene.duplicated_files.files[0].id_file:
                        self.stash.make_primary_file(scene.id, scene.duplicated_files.id_file)
                    for file_id in scene.duplicated_files.to_delete_files:
                        self.stash.delete_file(file_id)
                else:
                    for file_id in scene.duplicated_files.to_delete_files:
                        self.logger.log("File to delete: " + str(file_id))
        self.logger.log_end("DELETE DUPLICATES FILES")

    def process_scan(self):
       self.stash.scan()

    def process_corrupted(self, scenes_number_max, dry_run=True):
        self.logger.log_start("PROCESS CORRUPTED")
        scene_filter_str = {"phash_distance":
                                {"value": "0",
                                 "modifier": "IS_NULL"}
                            }
        scene_list = self.stash.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)

        if len(scene_list) == 0:
            self.logger.log("No scenes to delete")
        else:
            self.stash.destroy_scenes(dry_run, [elem.id for elem in scene_list], False)
        self.logger.log_end("PROCESS CORRUPTED")

    def process_trash(self, scenes_number_max, remote_paths, dry_run=True):
        self.logger.log_start("PROCESS TRASH")
        scene_filter_str = {"path":
                                {"value": remote_paths["Trash"],
                                 "modifier": "INCLUDES"}
                            }
        scene_list = self.stash.find_scenes_by_scene_filter(scene_filter_str, scenes_number_max)

        if len(scene_list) == 0:
            self.logger.log("No scenes to delete")
        else:
            self.stash.destroy_scenes(dry_run, [elem.id for elem in scene_list], True)
        self.logger.log_end("PROCESS TRASH")

    def process_reset_scene_path(self, path: str, reset_scene_max_number=500, dry_run=True):
        # remove tag MATCH_DONE from all scenes in a path
        self.logger.log_start("PROCESS RESET SCENE PATH")
        self.logger.log("Processing path: " + path + " with max scenes: " + str(reset_scene_max_number) + " (dry run: " + str(dry_run) + ")")
        tags_list: List[Tags] = self.stash.get_tags()

        scene_filter = SceneFilter(organized=False, tags_includes=[MATCHES_DONE],
                                   tags_excludes=([MATCHES_FILTERED, MATCHES_FALSE_POSITIVE]),
                                   path=path)
        scene_list = self.stash.find_scenes_by_tags_path(tags_list, scene_filter, reset_scene_max_number)
        self.stash.remove_tags(scene_list, [x for x in tags_list if x.name in [MATCHES_DONE]], dry_run)
        self.logger.log_end("PROCESS RESET SCENE PATH")

    def process_test(self, dry_run=True):
        # TODO: Complete the test. Use this method to test new code and API call
        self.logger.log_start("PROCESS Test")
        # Retrieve all tags from Stash
        tags_list: List[Tags] = self.stash.get_tags()

        self.logger.log_block(tags_list, "TAGS LIST")
        stashbox_list: List[StashBox] = self.stash.get_stashbox_list(tags_list)
        self.logger.log_block(stashbox_list, "STASHBOX LIST")

        scene_filter = SceneFilter(organized=False, tags_includes=[MATCHES_DONE],
                                   tags_excludes=([MATCHES_FILTERED, MATCHES_FALSE_POSITIVE]),
                                   path="/61.1_series/61.1.9.import/categories")
        scene_list = self.stash.find_scenes_by_tags_path(tags_list, scene_filter, 30)

        self.stash.remove_tags(scene_list, [x for x in tags_list if x.name in [MATCHES_DONE]], dry_run)
        self.logger.log_end("PROCESS Test")

    def main(self):

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
        parser.add_argument('--execute', action='store_true', help='Execute operations (default is dry-run)')
        parser.add_argument('--n', nargs="+", type=int, help='Number of scenes to process')

        args = parser.parse_args()
        dry_run = not args.execute
        num_scenes = args.n

        if args.scan:
            self.process_scan()

        if args.delete_duplicates_files:
            self.delete_duplicates_files(dry_run)

        if args.delete_duplicates_scenes:
            self.delete_duplicates_scenes(PhashDistance.EXACT, dry_run)
            self.delete_duplicates_scenes(PhashDistance.HIGH, dry_run)
            # delete_duplicates_scenes(stash, PhashDistance.MEDIUM, False)
            # delete_duplicates_scenes(stash, PhashDistance.LOW, False)

        if args.garbage:
            self.process_corrupted(self.query_max_number, dry_run)
            self.process_trash(self.query_max_number, self.paths, dry_run)
            self.remove_matches(dry_run)
            self.remove_false_matches(dry_run)


        if args.process_files:
            self.process_matches( self.query_max_number, dry_run)

        if args.update_scene_all:
            self.process_update_scene_all(dry_run)

        if args.update_scene_path:
            for x in args.path:
                self.process_update_scene_path(path=x, dry_run=dry_run)

        if args.reset_scene_path:
            for x in args.path:
                for y in range(1, 10):
                    self.logger.log("Resetting scene path - run number " + str(y) + "/" + str(10) + " (dry run: " + str(dry_run) + ")")
                    self.process_reset_scene_path(path=x, reset_scene_max_number=num_scenes, dry_run=dry_run)

        if args.test:
            self.process_test(dry_run)


if __name__ == "__main__":
    # TODO move Shoko integration in an other class
    # TODO fix log timezone
    # TODO add a method to remove tag UNKOWN from all scenes
    # TODO Add management of dimension in compare
    manage_stash = ManageStash()
    manage_stash.main()
