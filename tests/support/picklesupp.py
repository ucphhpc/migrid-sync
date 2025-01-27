import pickle

from tests.support.suppconst import TEST_OUTPUT_DIR
from tests.support.pathsupp import is_path_within


class PickleAssertMixin:
    def assertPickledFile(self, pickle_file_path):
        assert is_path_within(pickle_file_path, TEST_OUTPUT_DIR)

        with open(pickle_file_path, 'rb') as picklefile:
            return pickle.load(picklefile)
