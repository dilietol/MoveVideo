import time
from dataclasses import dataclass, field
from typing import List

from stashapi.stashapp import StashInterface

from FindBestFile import FileSlim, DuplicatedFiles
from Log import log


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
    path: str = ""


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
    urls: List[str] = field(init=False)
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
        self.urls = self.json["urls"]
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
        self.image = self.json["image"]
        self.file = self.json["file"]
        self.studio = Studio(json=self.json["studio"])
        self.performers = [Performer(json=p) for p in self.json["performers"]] if self.json[
                                                                                      "performers"] is not None else []
        self.remote_site_id = self.json["remote_site_id"]
        self.duration = self.json["duration"]
        self.fingerprints = [Fingerprints(json=f) for f in self.json["fingerprints"]]
        self.json = None


@dataclass
class Scrape:
    s: StashInterface
    scene: Scene
    stashbox: StashBox
    matches: List[Match] = field(init=False)
    calc_duration_matches_total: int = field(init=False)
    calc_duration_matches_number: int = field(init=False)
    calc_phashes_matches_exact: int = field(init=False)
    calc_phashes_matches_number: int = field(init=False)
    calc_match: bool = False

    def __post_init__(self) -> None:
        self.matches = find_matches(self.s, self.scene, self.stashbox)
        if len(self.scene.files) == 1 and self.matches is not None and len(self.matches) == 1:
            # One Match
            phashes = [y for y in self.matches[0].fingerprints if y.algorithm == "PHASH"]
            phash = self.scene.files[0].phash
            self.calc_duration_matches_total = len(self.matches[0].fingerprints)
            self.calc_duration_matches_number = sum(
                1 for x in self.matches[0].fingerprints if
                # differ for less than 1.5 seconds
                abs(x.duration - self.scene.files[0].duration) < 1.5
                # percentage of the entire length: difference in less than 0,3% (5 is acceptable for a length of 1930
                or ((abs(x.duration - self.scene.files[0].duration)) * 1000 / self.scene.files[0].duration) < 3)
            self.calc_phashes_matches_exact = sum(1 for x in phashes if x.hash == phash)

            n = 0
            if phash is not None:
                for x in phashes:
                    diff = 0
                    for i in range(min(len(x.hash), len(phash))):
                        if x.hash[i] != phash[i]:
                            diff += 1
                            if diff >= 4:
                                break
                    if diff < 4:
                        n += 1
            self.calc_phashes_matches_number = n
            self.calc_match = calc_match(self)
        else:
            # TODO: add a recognition method based on date when more than one match is found.
            self.calc_duration_matches_total = 0
            self.calc_duration_matches_number = 0
            self.calc_phashes_matches_exact = 0
            self.calc_phashes_matches_number = 0
            self.calc_match = False
        self.s = None


def calc_match(self: Scrape) -> bool:
    # TODO: add a more cases to match; currently only simple matches are managed
    result: bool = False
    same_date: bool = False
    if self.calc_phashes_matches_exact > 0 and self.calc_duration_matches_number == self.calc_duration_matches_total:
        # Exact and equal number
        result = True
    date_str_list = list(set([elem[-2:] for elem in self.matches[0].date.split("-")]))
    if len(date_str_list) == 3:
        same_date = all(elem in self.scene.files[0].basename for elem in date_str_list)
    if self.calc_phashes_matches_exact > 0 and self.calc_duration_matches_number > 5 and same_date is True:
        # Exact and number greater than 5 and date match
        result = True
    if self.calc_duration_matches_number == self.calc_duration_matches_total and same_date is True:
        # equal number and date match
        result = True

    return result


def find_matches(s: StashInterface, scene: Scene, stashbox: StashBox) -> List[Match]:
    # TODO: StashCli
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

    return result
