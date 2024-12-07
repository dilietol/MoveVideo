import time
from dataclasses import dataclass, field
from typing import List

from stashapi.stashapp import StashInterface

from FindBestFile import FileSlim, DuplicatedFiles


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
class MatchEvaluation:
    match: Match
    scene: Scene
    # file: FileSlim
    matched: bool = False  # True if at least one good match
    same_date: bool = False  # True if date match to filename
    duration_matches_total: int = field(init=False)  # number of match duration
    duration_matches_number: int = field(init=False)  # number match duration equal to file duration
    phashes_matches_exact: int = field(init=False)  # number of exact phase match
    phashes_matches_number: int = field(init=False)  # number of similar phashes match
    no_match_why: str = field(init=False)  # why for not matched

    def __post_init__(self) -> None:
        self.duration_matches_total, self.duration_matches_number = duration_match(self.match,
                                                                                   self.scene.files[
                                                                                       0].duration)
        self.phashes_matches_exact, self.phashes_matches_number = phashes_match(self.match,
                                                                                self.scene.files[0].phash)
        self.same_date = is_same_date(self.match, self.scene.files[0].basename)
        self.matched, self.no_match_why = is_match(self.match, self.scene.files[0].basename,
                                                   self.duration_matches_total,
                                                   self.duration_matches_number,
                                                   self.phashes_matches_exact, self.phashes_matches_number)

    def get_why(self) -> str:
        return self.no_match_why + " (" + str(self.duration_matches_total) + "/" + str(
            self.duration_matches_number) + "/" + str(self.phashes_matches_exact) + "/" + str(
            self.phashes_matches_number) + "/" + str(self.same_date) + ")"


def duration_match(match: Match, duration: float) -> (int, int):
    # Calc the number of match duration (total) and number of match duration equal to file duration (number)
    return len(match.fingerprints), sum(
        1 for x in match.fingerprints if
        # differ for less than 1.5 seconds
        abs(x.duration - duration) < 1.5
        # percentage of the entire length: difference in less than 0,3% (5 is acceptable for a length of 1930
        or ((abs(x.duration - duration)) * 1000 / duration) < 3)


def phashes_match(match: Match, phash: str) -> (int, int):
    # Calc the number of exact phase match and number of similar phashes match
    # The calculation is made only on PHASH fingerprints
    phashes = [y for y in match.fingerprints if y.algorithm == "PHASH"]
    return sum(1 for x in phashes if x.hash == phash), sum(
        1 for x in phashes if sum(1 for a, b in zip(x.hash, phash) if a != b) <= 4)


def is_same_date(match: Match, filename: str) -> bool:
    # Check if the date of the match is the same as the date of the filename
    date_str_list = list(set([elem[-2:] for elem in match.date.split("-")]))
    if len(date_str_list) == 3:
        return all(elem in filename for elem in date_str_list)
    return False


def is_match(match: Match, filename: str, duration_matches_total: int, duration_matches_number: int,
             phashes_matches_exact: int, phashes_matches_number: int) -> (bool, str):
    # TODO: add a more cases to match; currently only simple matches are managed
    result: bool = False
    same_date: bool = False
    if phashes_matches_exact > 0 and (
            duration_matches_number == duration_matches_total or duration_matches_number >= 10):
        # At least one Exact match and all duration equal or duration equal number >= 10
        result = True
    elif phashes_matches_number > 1 and duration_matches_number == duration_matches_total:
        # At least one similar match and all duration equal
        result = True
    same_date = is_same_date(match, filename)
    if phashes_matches_exact > 0 and duration_matches_number > 5 and same_date is True:
        # At least one Exact match and duration equal number > 5 and date match
        result = True
    elif duration_matches_number == duration_matches_total and same_date is True:
        #  all duration equal and date match
        result = True

    return result, "" if result is True else "No good match found"


@dataclass
class Scrape:
    s: StashInterface
    scene: Scene
    stashbox: StashBox
    matches: List[Match] = field(init=False)
    evaluations: List[MatchEvaluation] = field(init=False)
    match: bool = False  # True if at least one good match
    match_why: str = field(init=False)  # why for not matched
    index: int = -1  # the evaluations sequence that matched
    match_object: Match = field(init=False)

    def __post_init__(self) -> None:
        self.matches = find_matches(self.s, self.scene, self.stashbox)
        if len(self.scene.files) == 1 and self.matches is not None:
            self.evaluations = [MatchEvaluation(x, self.scene) for x in self.matches]
            if len(self.matches) == 1:
                # One Match
                self.match = any(x.matched for x in self.evaluations)
                self.index = 0
                self.match_object = self.evaluations[0].match
                self.match_why = self.evaluations[0].get_why()
            else:
                # TODO: add a recognition method based on date when more than one match is found.
                self.match = any(x.matched for x in self.evaluations)
                if self.match:
                    matches_list = [x for x in self.evaluations if x.matched]
                    if len(matches_list) == 1:
                        self.match_object = matches_list[0].match
                        self.index = 1
                    else:
                        matches_date_list = [x for x in self.evaluations if x.matched and x.same_date]
                        if len(matches_date_list) == 1:
                            self.match_object = matches_date_list[0].match
                            self.index = 1
                        else:
                            self.index = -1
                            self.match_why = "More than one match : " + " - ".join(
                                x.match.title + " -> " + x.get_why() for x in self.evaluations)
                else:
                    self.index = -1
                    self.match_why = "More than one match : " + " - ".join(
                        x.match.title + " -> " + x.get_why() for x in self.evaluations)
        else:
            # No match possible
            self.match = False
            self.index = -1
            if len(self.scene.files) == 1:
                self.match_why = "No match found"
            elif len(self.scene.files) > 1:
                self.match_why = "many files"
            elif len(self.scene.files) < 1:
                self.match_why = "no file"
            self.evaluations = []
        self.s = None


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
            print(f"Received a GraphQL exception : {e}")
            time.sleep(4)
            data = None

    if data is not None:
        # Process the scraped data and create Match objects
        for elem in data:
            result.append(Match(json=elem))

    return result
