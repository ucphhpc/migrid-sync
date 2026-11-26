import os

from mig.lib import fs
from tests.support import MigTestCase


class TestMkdir(MigTestCase):

    def test_creates_directory_with_default_mode(self) -> None:
        path = os.path.join(self.temppath("mkdir"), "created")

        fs.mkdir(path)
        actual = os.stat(path)

        self.assertEqual(actual.st_mode & 0o777, 0o700)

    def test_creates_directory_with_given_mode(self) -> None:
        path = os.path.join(self.temppath("mkdir"), "created")

        fs.mkdir(path, mode=0o651)
        actual = os.stat(path)

        self.assertEqual(actual.st_mode & 0o777, 0o651)

    def test_raises_exception_if_directory_exists(self) -> None:
        tmp = self.temppath("mkdir")
        path = os.path.join(tmp, "directory")
        os.mkdir(path)

        with self.assertRaises(FileExistsError):
            fs.mkdir(path)

    def test_raises_exception_if_file_exists(self) -> None:
        tmp = self.temppath("mkdir")
        path = os.path.join(tmp, "file")
        with open(path, "w") as tmpfile:
            tmpfile.write("content")

        with self.assertRaises(FileExistsError):
            fs.mkdir(path)

    def test_raises_exception_parent_directory_does_not_exist(self) -> None:
        tmp = self.temppath("mkdir")
        path = os.path.join(tmp, "nonexisting", "created")

        with self.assertRaises(FileNotFoundError):
            fs.mkdir(path)


class TestMakedirs(MigTestCase):

    def test_creates_directories_with_default_mode(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2", "level3")

        fs.makedirs(path)
        stat1 = os.stat(os.path.join(tmp, "level1"))
        stat2 = os.stat(os.path.join(tmp, "level1", "level2"))
        stat3 = os.stat(os.path.join(tmp, "level1", "level2", "level3"))

        self.assertEqual(stat1.st_mode & 0o777, 0o700)
        self.assertEqual(stat2.st_mode & 0o777, 0o700)
        self.assertEqual(stat3.st_mode & 0o777, 0o700)

    def test_creates_directories_with_given_mode(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2", "level3")

        fs.makedirs(path, mode=0o751)
        stat1 = os.stat(os.path.join(tmp, "level1"))
        stat2 = os.stat(os.path.join(tmp, "level1", "level2"))
        stat3 = os.stat(os.path.join(tmp, "level1", "level2", "level3"))

        self.assertEqual(stat1.st_mode & 0o777, 0o751)
        self.assertEqual(stat2.st_mode & 0o777, 0o751)
        self.assertEqual(stat3.st_mode & 0o777, 0o751)

    def test_raises_exception_if_file_exists(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "file")
        with open(path, "w") as tmpfile:
            tmpfile.write("content")

        with self.assertRaises(FileExistsError):
            fs.makedirs(path)

    def test_does_not_raise_exception_if_nonleaf_directory_exists(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2")
        os.mkdir(os.path.join(tmp, "level1"))

        fs.makedirs(path)

        self.assertIsNotNone(os.stat(path))

    def test_raises_exception_if_leaf_directory_exists(self) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2")
        os.makedirs(path)

        with self.assertRaises(FileExistsError):
            fs.makedirs(path)

    def test_does_not_raise_exception_when_leaf_directory_exists_if_exist_ok(
        self,
    ) -> None:
        tmp = self.temppath("makedirs")
        path = os.path.join(tmp, "level1", "level2")
        os.makedirs(path)

        fs.makedirs(path, exist_ok=True)

        self.assertIsNotNone(os.stat(path))
