from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class FileSlim:
    # File info
    id: int
    organized: bool
    width: int
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
    id: int = field(init=False)  # id of the file to keep
    why: str = field(init=False)  # reason why the file was selected or not
    to_delete: List[int] = field(init=False, default_factory=list)  # list of files to delete
    to_delete_size: float = field(init=False)  # size of files to delete

    def __post_init__(self) -> None:
        self.id = 0
        self.why = "NA"
        self.to_delete = []
        self.to_delete_size = 0
        if len(self.files) == 0:
            self.id = 0
            self.why = "No files"
        elif len(self.files) == 1:
            self.id = 0
            self.why = "No duplicates"
        else:
            if not is_duration_correct(self.files):
                self.id = 0
                self.why = "Duration not valid"
            else:
                organized_requested = not check_organized(self.files)
                files_dict_2 = select_by_width(self.files)
                if len(files_dict_2) == 0:
                    self.id = 0
                    self.why = "Not good width"
                elif len(files_dict_2) == 1:
                    if organized_requested and not files_dict_2[0].organized:
                        self.id = 0
                        self.why = "Best width not organized"
                    else:
                        self.id = files_dict_2[0].id
                        self.why = "Best width"
                        self.to_delete, self.to_delete_size = files_to_delete(self.files, self.id)
                else:
                    files_dict_3 = select_by_codec(files_dict_2)
                    if len(files_dict_3) == 0:
                        self.id = 0
                        self.why = "Not good codec"
                    elif len(files_dict_3) == 1:
                        if organized_requested and not files_dict_3[0].organized:
                            self.id = 0
                            self.why = "Best codec not organized"
                        else:
                            self.id = files_dict_3[0].id
                            self.why = "Best codec"
                            self.to_delete, self.to_delete_size = files_to_delete(self.files, self.id)
                    else:
                        files_dict_4 = select_by_size(files_dict_3)
                        if len(files_dict_4) == 0:
                            self.id = 0
                            self.why = "Not good size"
                        elif len(files_dict_4) == 1:
                            if organized_requested and not files_dict_4[0].organized:
                                self.id = 0
                                self.why = "Best size not organized"
                            else:
                                self.id = files_dict_4[0].id
                                self.why = "Best size"
                                self.to_delete, self.to_delete_size = files_to_delete(self.files, self.id)
                        else:
                            organized_one = [elem for elem in files_dict_4 if elem.organized]
                            if len(organized_one) == 1:
                                self.id = organized_one[0].id
                                self.why = "One organized among equal files"
                                self.to_delete, self.to_delete_size = files_to_delete(self.files, self.id)
                            elif len(organized_one) > 1:
                                self.id = organized_one[0].id
                                self.why = "Selected among many organized equal files"
                                self.to_delete, self.to_delete_size = files_to_delete(self.files, self.id)
                            else:
                                self.id = 0
                                self.why = "No organized among equal file"


def check_organized(array: list[FileSlim]):
    first_value = array[0].organized
    for elem in array:
        if elem.organized != first_value:
            return False
    return True


def is_duration_correct(array: List[FileSlim]) -> bool:
    first_value = float(array[0].duration)
    if first_value < 600:
        return False
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


def files_to_delete(files_dict: list[FileSlim], best_file_id: int):
    return list(filter(lambda x: x != best_file_id, [elem.id for elem in files_dict])), round(
        (sum([elem.size for elem in files_dict if
              elem.id != best_file_id]) / 1024 / 1024 / 1024), 2)
