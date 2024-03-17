from dataclasses import dataclass
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
    oshash: str
    phash: str
    format: str



@dataclass
class DuplicatedFiles:
    # File comparison result
    files: List[FileSlim]  # list of files to compare
    id: int  # id of the file to keep
    why: str  # reason why the file was selected or not
    to_delete: List[int]  # list of files to delete
    to_delete_size: float  # size of files to delete

#TODO: implementare l'automatismo per valorizzare bene le varibili interne come descritto qui https://www.youtube.com/watch?v=5mMpM8zK4pY
#TODO: gestione dei file senza phash come per i corrotti


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
            result.why = "Best width not organized"
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
            result.why = "Best codec not organized"
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
            result.why = "Best size not organized"
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
