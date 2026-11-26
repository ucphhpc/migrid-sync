import os


def mkdir(path: str, *, mode: int = 0o700) -> None:
    """Create the given directory.

    Args:
        path: the path to create the directory at.
        mode: the mode to create the directory with.
    Raises:
        OSError: different subclasses corresponding to the error.
    """
    os.mkdir(path, mode)


def makedirs(path: str, *, mode: int = 0o700, exist_ok: bool = False) -> None:
    """Create the given directories recursively.

    Args:
        path: the path to create the directories at.
        mode: the mode to create the directories with.
        exist_ok: if True do not raise an error when the leaf directory already
            exists, if False do raise an error.
    Raises:
        OSError: different subclasses corresponding to the error.
    """
    # create intermediate directories
    split_path = os.path.normpath(path).split(os.path.sep)[:-1]
    for i in range(len(split_path)-1):
        intermediate_path = os.path.sep.join(split_path[0:i+2])
        try:
            mkdir(intermediate_path, mode=mode)
        except FileExistsError:
            if not os.path.isdir(intermediate_path):
                raise
    
    # create leaf directory
    try:
        mkdir(path, mode=mode)
    except FileExistsError:
        if not exist_ok:
            raise
        if not os.path.isdir(path):
            raise
