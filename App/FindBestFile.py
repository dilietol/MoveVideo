import os
from dataclasses import dataclass, field
from idlelib.run import idle_formatwarning
from typing import Any, List


@dataclass
class FileSlim:
    # File info
    id: int
    id_file: int
    organized: bool
    width: int
    height: int
    video_codec: float
    size: int
    duration: float
    basename: str
    oshash: str | None
    phash: str | None
    format: str


@dataclass
class DuplicatedFiles:
    # File comparison result
    files: List[FileSlim]  # list of files to compare
    id: int = field(init=False)  # id of the scene to keep
    id_file: int = field(init=False)  # id of the file to keep
    why: str = field(init=False)  # reason why the file was selected or not
    to_delete: List[int] = field(init=False, default_factory=list)  # list of scenes to delete
    to_delete_files: List[int] = field(init=False, default_factory=list)  # list of files to delete
    to_delete_size: float = field(init=False)  # size of files to delete

    def __post_init__(self) -> None:
        self.id = 0
        self.id_file = 0
        self.why = "NA"
        self.to_delete = []
        self.to_delete_files = []
        self.to_delete_size = 0
        if len(self.files) == 0:
            self.id = 0
            self.id_file = 0
            self.why = "No files"
        elif len(self.files) == 1:
            self.id = 0
            self.id_file = 0
            self.why = "No duplicates"
        else:
            if not is_duration_minimum(self.files):
                self.id = 0
                self.id_file = 0
                self.why = "Duration below minimum"
            elif not is_duration_correct(self.files):
                self.id = 0
                self.id_file = 0
                self.why = "Duration not valid"
            else:
                organized_requested = not check_organized(self.files)
                files_dict_2 = select_by_height(self.files)
                if len(files_dict_2) == 0:
                    self.id = 0
                    self.id_file = 0
                    self.why = "Not good height"
                elif len(files_dict_2) == 1:
                    if organized_requested and not files_dict_2[0].organized:
                        self.id = 0
                        self.id_file = 0
                        self.why = "Best height not organized"
                    else:
                        self.id = files_dict_2[0].id
                        self.id_file = files_dict_2[0].id_file
                        self.why = "Best height"
                        self.to_delete, self.to_delete_files, self.to_delete_size = files_to_delete(self.files, self.id,
                                                                                                    self.id_file)
                else:
                    files_dict_3 = select_by_codec(files_dict_2)
                    if len(files_dict_3) == 0:
                        self.id = 0
                        self.id_file = 0
                        self.why = "Not good codec"
                    elif len(files_dict_3) == 1:
                        if organized_requested and not files_dict_3[0].organized:
                            self.id = 0
                            self.id_file = 0
                            self.why = "Best codec not organized"
                        else:
                            self.id = files_dict_3[0].id
                            self.id_file = files_dict_3[0].id_file
                            self.why = "Best codec"
                            self.to_delete, self.to_delete_files, self.to_delete_size = files_to_delete(self.files,
                                                                                                        self.id,
                                                                                                        self.id_file)
                    else:
                        files_dict_4 = select_by_size(files_dict_3)
                        if len(files_dict_4) == 0:
                            self.id = 0
                            self.id_file = 0
                            self.why = "Not good size"
                        elif len(files_dict_4) == 1:
                            if organized_requested and not files_dict_4[0].organized:
                                self.id = 0
                                self.id_file = 0
                                self.why = "Best size not organized"
                            else:
                                self.id = files_dict_4[0].id
                                self.id_file = files_dict_4[0].id_file
                                self.why = "Best size"
                                self.to_delete, self.to_delete_files, self.to_delete_size = files_to_delete(self.files,
                                                                                                            self.id,
                                                                                                            self.id_file)
                        else:
                            organized_one = [elem for elem in files_dict_4 if elem.organized]
                            if len(organized_one) == 1:
                                self.id = organized_one[0].id
                                self.id_file = organized_one[0].id_file
                                self.why = "One organized among equal files"
                                self.to_delete, self.to_delete_files, self.to_delete_size = files_to_delete(self.files,
                                                                                                            self.id,
                                                                                                            self.id_file)
                            elif len(organized_one) > 1:
                                self.id, self.id_file = select_among_equal_organized(organized_one)
                                self.why = "Selected among many organized equal files"
                                self.to_delete, self.to_delete_files, self.to_delete_size = files_to_delete(self.files,
                                                                                                            self.id,
                                                                                                            self.id_file)
                            else:
                                self.id = 0
                                self.id_file = 0
                                self.why = "No organized among equal file"


def check_organized(array: list[FileSlim]):
    first_value = array[0].organized
    for elem in array:
        if elem.organized != first_value:
            return False
    return True


def is_duration_minimum(array: List[FileSlim]) -> bool:
    threshold = 540
    first_value = float(array[0].duration)
    if first_value < threshold:
        return False
    for elem in array:
        if float(elem.duration) < threshold:
            return False
    return True


def is_duration_correct(array: List[FileSlim]) -> bool:
    first_value = float(array[0].duration)
    for elem in array:
        # TODO: review this rule because is very taffy, in other cases (like fingerprints) we used a 3/1000 difference
        if abs((float(elem.duration) - first_value) / first_value) > 0.0005:
            return False
    return True


def select_by_width(files_dict: List[FileSlim]) -> List[FileSlim]:
    # Find the maximum value of the attribute "width"
    max_width = max(elem.width for elem in files_dict)

    # Select all occurrences with attribute 'width' equal to the maximum value
    matching_elements: list[FileSlim] = [elem for elem in files_dict if elem.width == max_width]
    return matching_elements

def select_by_height(files_dict: List[FileSlim]) -> List[FileSlim]:
    # Find the maximum value of the attribute "height"
    max_height = max(elem.height for elem in files_dict)
    # Select all occurrences with attribute 'height' equal to the maximum value
    matching_elements: list[FileSlim] = [elem for elem in files_dict if elem.height == max_height]

    elements_1080: list[FileSlim] = [elem for elem in files_dict if elem.height == 1080]
    if len(elements_1080) >= 1:
        matching_elements = elements_1080
    else:
        elements_720: list[FileSlim] = [elem for elem in files_dict if elem.height == 720]
        if len(elements_720) >= 1:
            matching_elements = elements_720
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


def files_to_delete(files_dict: list[FileSlim], best_scene_id: int, best_file_id: int):
    return (list(filter(lambda x: x != best_scene_id, [elem.id for elem in files_dict])),
            list(filter(lambda x: x != best_file_id, [elem.id_file for elem in files_dict])),
            round(
                (sum([elem.size for elem in files_dict if
                      elem.id_file != best_file_id]) / 1024 / 1024 / 1024), 2))


def select_among_equal_organized(organized_one: [FileSlim]):
    id = organized_one[0].id
    id_file = organized_one[0].id_file

    # Unselect files with "None" name
    candidates1: List[FileSlim] = []
    for elem in organized_one:
        if not elem.basename.startswith("None"):
            candidates1.append(elem)
    if len(candidates1) == 1:
        id = candidates1[0].id
        id_file = candidates1[0].id_file
    elif len(candidates1) > 1:
        # Unselect files with suffix "_1"
        min_elem = min(candidates1, key=lambda x: len(x.basename))
        min_value = len(min_elem.basename)
        if min_value > 20:
            nomebase = os.path.splitext(min_elem.basename)[0]
            if all(elem.basename.startswith(f"{nomebase}") for elem in candidates1):
                id = min_elem.id
                id_file = min_elem.id_file
    return id, id_file
