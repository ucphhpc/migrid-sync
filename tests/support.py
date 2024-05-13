import errno
import os
import shutil
import stat
import sys
from unittest import TestCase, main as testmain

TEST_BASE = os.path.dirname(__file__)
TEST_OUTPUT_DIR = os.path.join(TEST_BASE, "output")
MIG_BASE = os.path.realpath(os.path.join(TEST_BASE, ".."))

# All MiG related code will at some point include bits
# from the mig module namespace. Rather than have this
# knowledge spread through every test file, make the
# sole responsbility of test files to find the support
# file and configure the rest here.
sys.path.append(MIG_BASE)

# provision an output directory up-front
try:
    os.mkdir(TEST_OUTPUT_DIR)
except EnvironmentError as e:
    if e.errno == errno.EEXIST: pass # FileExistsError

class FakeLogger:
    CHANNELS = [
        'error',
    ]

    def __init__(self):
        self.channels_dict = FakeLogger.create_channels_dict()

    def _append_as(self, channel, line):
        self.channels_dict[channel].append(line)

    def debug(self, line):
        self._append_as('debug', line)

    def error(self, line):
        self._append_as('error', line)

    def info(self, line):
        self._append_as('info', line)

    def warning(self, line):
        self._append_as('warning', line)

    @classmethod
    def create_channels_dict(cls):
        return dict(((channel, []) for channel in cls.CHANNELS))

class MigTestCase(TestCase):
    def __init__(self, *args):
        super(MigTestCase, self).__init__(*args)
        self._cleanup_paths = set()
        self._logger = None

    def tearDown(self):
        self._logger = None

        for path in self._cleanup_paths:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
            else:
                continue

    @property
    def logger(self):
        if self._logger is None:
            self._logger = FakeLogger()
        return self._logger

    def assertPathExists(self, relative_path):
        assert(not os.path.isabs(relative_path)), "expected relative path within output folder"
        absolute_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
        stat_result = os.stat(absolute_path)
        if stat.S_ISDIR(stat_result.st_mode):
            return "dir"
        else:
            return "file"

def cleanpath(relative_path, test_case):
    assert(isinstance(test_case, MigTestCase))
    tmp_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
    test_case._cleanup_paths.add(tmp_path)

def temppath(relative_path, test_case, skip_clean=False):
    assert(isinstance(test_case, MigTestCase))
    tmp_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
    if not skip_clean:
        test_case._cleanup_paths.add(tmp_path)
    return tmp_path
