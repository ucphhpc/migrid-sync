import errno
import os
import shutil
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

class MigTestCase(TestCase):
    def __init__(self, *args):
        super(MigTestCase, self).__init__(*args)
        self._cleanup_paths = set()

    def tearDown(self):
        for path in self._cleanup_paths:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

def temppath(relative_path, test_case=None):
    tmp_path = os.path.join(TEST_OUTPUT_DIR, relative_path)
    if isinstance(test_case, MigTestCase):
        test_case._cleanup_paths.add(tmp_path)
    return tmp_path
