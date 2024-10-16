import argparse


_EMPTY_DICT = {}
_NO_DEFAULT = object()

def _arg_name_to_flag(arg_name):
    return ''.join(('--', arg_name))


def _arg_name_to_default(arg_name, _defaults):
    try:
        return _defaults[arg_name]
    except KeyError:
        return None


def minimist(prog, description, epilog, string=[], boolean=[], integers=[], _defaults=None):
    parser = argparse.ArgumentParser(prog, allow_abbrev=False)

    if _defaults is None:
        _defaults = {}

    for arg_name in boolean:
        parser.add_argument(_arg_name_to_flag(arg_name), action='store_true')

    for arg_name in string:
        arg_default = _defaults.get(arg_name, None)
        parser.add_argument(_arg_name_to_flag(arg_name), default=arg_default)

    for arg_name in integers:
        parser.add_argument(_arg_name_to_flag(arg_name), type=int)

    return parser
