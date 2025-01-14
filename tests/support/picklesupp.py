import pickle

from tests.support._path import verify_path_within_output_dir_and_return, \
    is_path_within


class PickleAssertMixin:
    def assertPickledFile(self, pickle_file):
        tmp_path = verify_path_within_output_dir_and_return(pickle_file)

        with open(tmp_path, 'rb') as picklefile:
            return pickle.load(picklefile)
