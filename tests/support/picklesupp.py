import pickle

from tests.support._path import ensure_path_within_output_dir, \
    is_path_within


class PickleAssertMixin:
    def assertPickledFile(self, pickle_file):
        ensure_path_within_output_dir(pickle_file)

        with open(pickle_file, 'rb') as picklefile:
            return pickle.load(picklefile)
