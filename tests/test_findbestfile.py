import unittest
import sys
# Aggiunge la cartella App/ (dove si trova FindBestFile.py) al path
if r'C:\\Users\\dilie\\PycharmProjects\\MoveVideo\\App' not in sys.path:
    sys.path.insert(0, r'C:\\Users\\dilie\\PycharmProjects\\MoveVideo\\App')
from App.FindBestFile import FileSlim, is_duration_minimum, is_duration_correct, check_organized, DuplicatedFiles

class TestFileSlimAttributes(unittest.TestCase):
    """Test per gli attributi di FileSlim."""

    def test_video_codec_is_str(self):
        f = FileSlim(id=1, id_file=1, organized=True, width=1920, height=1080, video_codec="hevc", size=1000, duration=60.0,
                     basename="test.mkv", format="mkv", oshash=None, phash=None)
        self.assertIsInstance(f.video_codec, str)

    def test_duration_is_float(self):
        f = FileSlim(id=1, id_file=1, organized=True, width=1920, height=1080, video_codec="hevc", size=1000, duration=60.0,
                     basename="test.mkv", format="mkv", oshash=None, phash=None)
        self.assertIsInstance(f.duration, float)

    def test_basename_and_format(self):
        f = FileSlim(id=1, id_file=1, organized=True, width=1920, height=1080, video_codec="hevc", size=1000, duration=60.0,
                     basename="test.mkv", format="mkv", oshash=None, phash=None)
        self.assertIsInstance(f.basename, str)
        self.assertIsInstance(f.format, str)

class TestDurationFunctions(unittest.TestCase):
    def setUp(self):
        self.files_ok = [
            FileSlim(id=1, id_file=1, organized=True, width=1920, height=1080, video_codec="hevc", size=1000, duration=120.0,
                     basename="a.mkv", format="mkv", oshash=None, phash=None),
            FileSlim(id=2, id_file=2, organized=True, width=1920, height=1080, video_codec="h264", size=1000, duration=90.0,
                     basename="b.mkv", format="mkv", oshash=None, phash=None),
        ]
        self.files_short = [
            FileSlim(id=1, id_file=1, organized=True, width=1920, height=1080, video_codec="hevc", size=1000, duration=0.1,
                     basename="c.mkv", format="mkv", oshash=None, phash=None),
        ]

    def test_is_duration_minimum_ok(self):
        self.assertTrue(is_duration_minimum(self.files_ok))

    def test_is_duration_minimum_too_short(self):
        self.assertFalse(is_duration_minimum(self.files_short))

    def test_is_duration_correct_ok(self):
        self.assertTrue(is_duration_correct(self.files_ok))

    def test_check_organized_true(self):
        organized_files = [
            FileSlim(id=1, id_file=1, organized=True, width=1920, height=1080, video_codec="hevc", size=1000, duration=60.0,
                     basename="a.mkv", format="mkv", oshash=None, phash=None)
        ]
        self.assertTrue(check_organized(organized_files))

    def test_check_organized_false(self):
        not_organized_files = [
            FileSlim(id=1, id_file=1, organized=False, width=1920, height=1080, video_codec="hevc", size=1000, duration=60.0,
                     basename="a.mkv", format="mkv", oshash=None, phash=None)
        ]
        self.assertFalse(check_organized(not_organized_files))

class TestDuplicatedFilesInitialization(unittest.TestCase):
    def setUp(self):
        self.files = [
            FileSlim(id=1, id_file=1, organized=True, width=1920, height=1080, video_codec="hevc", size=1000, duration=60.0,
                     basename="a.mkv", format="mkv", oshash=None, phash=None),
            FileSlim(id=2, id_file=2, organized=False, width=1920, height=1080, video_codec="h264", size=1000, duration=60.0,
                     basename="b.mkv", format="mkv", oshash=None, phash=None),
        ]
        self.df = DuplicatedFiles(files=self.files)

    def test_df_has_id_and_why(self):
        self.assertIsInstance(self.df.id, int)
        self.assertIsInstance(self.df.id_file, int)
        self.assertIsInstance(self.df.why, str)
        self.assertIsInstance(self.df.to_delete, list)
        self.assertIsInstance(self.df.to_delete_files, list)
        self.assertIsInstance(self.df.to_delete_size, float)

if __name__ == "__main__":
    unittest.main()