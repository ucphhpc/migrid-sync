from collections import defaultdict
import errno
import logging
import os
import re
import shutil
import stat
import sys
from unittest import TestCase, main as testmain

TEST_BASE = os.path.dirname(__file__)
TEST_OUTPUT_DIR = os.path.join(TEST_BASE, "output")
MIG_BASE = os.path.realpath(os.path.join(TEST_BASE, ".."))
PY2 = sys.version_info[0] == 2

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
    if e.errno == errno.EEXIST:
        pass  # FileExistsError

# basic global logging configuration for testing
#
# arrange a stream that ignores all logging messages


class BlackHole:
    def write(self, message):
        pass


BLACKHOLE_STREAM = BlackHole()
# provide a working logging setup (black hole by default)
logging.basicConfig(stream=BLACKHOLE_STREAM)
# request capturing warnings from within the Python runtime
logging.captureWarnings(True)


class FakeLogger:
    RE_UNCLOSEDFILE = re.compile(
        'unclosed file <.*? name=\'(?P<location>.*?)\'( .*?)?>')

    def __init__(self):
        self.channels_dict = defaultdict(list)
        self.unclosed_by_file = defaultdict(list)

    def _append_as(self, channel, line):
        self.channels_dict[channel].append(line)

    def check_empty_and_reset(self):
        unclosed_by_file = self.unclosed_by_file

        # reset the record of any logged messages
        self.channels_dict = defaultdict(list)
        self.unclosed_by_file = defaultdict(list)

        # complain loudly (and in detail) in the case of unclosed files
        if len(unclosed_by_file) > 0:
            messages = '\n'.join({' --> %s: line=%s, file=%s' % (fname, lineno, outname)
                                 for fname, (lineno, outname) in unclosed_by_file.items()})
            raise RuntimeError('unclosed files encountered:\n%s' % (messages,))

    def debug(self, line):
        self._append_as('debug', line)

    def error(self, line):
        self._append_as('error', line)

    def info(self, line):
        self._append_as('info', line)

    def warning(self, line):
        self._append_as('warning', line)

    def write(self, message):
        channel, namespace, specifics = message.split(':', maxsplit=2)

        # ignore everything except warnings sent by th python runtime
        if not (channel == 'WARNING' and namespace == 'py.warnings'):
            return

        filename_and_datatuple = FakeLogger.identify_unclosed_file(specifics)
        if filename_and_datatuple is not None:
            self.unclosed_by_file.update((filename_and_datatuple,))

    @staticmethod
    def identify_unclosed_file(specifics):
        filename, lineno, exc_name, message = specifics.split(':', maxsplit=3)
        exc_name = exc_name.lstrip()
        if exc_name != 'ResourceWarning':
            return
        matched = FakeLogger.RE_UNCLOSEDFILE.match(message.lstrip())
        if matched is None:
            return
        relative_testfile = os.path.relpath(filename, start=MIG_BASE)
        relative_outputfile = os.path.relpath(
            matched.groups('location')[0], start=TEST_BASE)
        return (relative_testfile, (lineno, relative_outputfile))


class MigTestCase(TestCase):
    def __init__(self, *args):
        super(MigTestCase, self).__init__(*args)
        self._cleanup_paths = set()
        self._logger = None
        self._skip_logging = False

    def setUp(self):
        if not self._skip_logging:
            self._reset_logging(stream=self.logger)

    def tearDown(self):
        if not self._skip_logging:
            self._logger.check_empty_and_reset()
        if self._logger is not None:
            self._reset_logging(stream=BLACKHOLE_STREAM)

        for path in self._cleanup_paths:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
            else:
                continue

    def _reset_logging(self, stream):
        root_logger = logging.getLogger()
        root_handler = root_logger.handlers[0]
        root_handler.stream = stream

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
