import os

from tests.support.suppconst import TEST_OUTPUT_DIR, ENVHELP_OUTPUT_DIR


def is_path_within(path, start=None, _msg=None):
    """Check if path is within start directory"""
    try:
        assert os.path.isabs(path), _msg
        relative = os.path.relpath(path, start=start)
    except:
        return False
    return not relative.startswith('..')


def ensure_path_within_output_dir(relative_path):
    if os.path.isabs(relative_path):
        # the only permitted paths are those within the output directory set
        # aside for execution of the test suite: this will be enforced below
        # so effectively submit the supplied path for scrutiny
        tmp_path = relative_path
    else:
        tmp_path = os.path.join(TEST_OUTPUT_DIR, relative_path)

    # failsafe path checking that supplied paths are rooted within valid paths
    is_tmp_path_within_safe_dir = False
    for start in (ENVHELP_OUTPUT_DIR):
        is_tmp_path_within_safe_dir = is_path_within(tmp_path, start=start)
        if is_tmp_path_within_safe_dir:
            break
    if not is_tmp_path_within_safe_dir:
        raise AssertionError("ABORT: corrupt test path=%s" % (tmp_path,))

    return tmp_path
