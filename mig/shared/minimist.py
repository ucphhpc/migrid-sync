import argparse


_EMPTY_DICT = {}
_NO_DEFAULT = object()
_POSITIONAL_MARKER = '__args__'


class GetoptCompatNamespace(argparse.Namespace):
    def __iter__(self):
        return iter(("-%s" % (k,), v) for k, v in self.__dict__.items() if k != _POSITIONAL_MARKER)


def _arg_name_to_flag(arg_name, is_getopt):
    if is_getopt:
        flag_prefix = "-"
    else:
        flag_prefix = "--"
    return ''.join((flag_prefix, arg_name))


def _arg_name_to_default(arg_name, _defaults):
    try:
        return _defaults[arg_name]
    except KeyError:
        return None


def minimist(prog, description, strings=[], booleans=[], integers=[],
             help_by_argument=_EMPTY_DICT, name_by_argument=_EMPTY_DICT,
             is_getopt=False, use_positional=False, _defaults=None):
    parser = argparse.ArgumentParser(prog, allow_abbrev=False)

    if _defaults is None:
        _defaults = {}

    for arg_name in booleans:
        arg_flag = _arg_name_to_flag(arg_name, is_getopt)
        parser.add_argument(arg_flag, action='store_true',
                            help=help_by_argument.get(arg_name, None))

    for arg_name in strings:
        if is_getopt:
            arg_fallback = argparse.SUPPRESS
        else:
            arg_fallback = None
        arg_default = _defaults.get(arg_name, arg_fallback)
        arg_flag = _arg_name_to_flag(arg_name, is_getopt)
        parser.add_argument(arg_flag, default=arg_default,
                            metavar=name_by_argument.get(arg_name),
                            help=help_by_argument.get(arg_name, None))

    for arg_name in integers:
        arg_flag = _arg_name_to_flag(arg_name, is_getopt)
        parser.add_argument(arg_flag, type=int,
                            metavar=name_by_argument.get(arg_name),
                            help=help_by_argument.get(arg_name, None))

    if is_getopt or use_positional:
        if is_getopt:
            arg_fallback = argparse.SUPPRESS
        else:
            arg_fallback = None
        parser.add_argument(_POSITIONAL_MARKER, nargs='*',
                            default=arg_fallback)

    return parser


def _parse_getopt_string(getopt_string):
    split_args = getopt_string.split(':')

    seen_string_args = set()

    boolean_arguments = []
    string_arguments = []

    # handle corner case of no arguments with value i.e. no separator in input
    # FIXME: ...

    def add_string_argument(arg):
        if arg == 'h':  # exclude -h which is handled internally by argparse
            return
        string_arguments.append(arg)

    index_of_last_entry = len(split_args) - 1

    for index, entry in enumerate(split_args):
        entry_length = len(entry)
        if entry_length == 1:
            if index == index_of_last_entry:
                boolean_arguments.append(entry)
            else:
                add_string_argument(entry)
        elif entry_length > 1:
            entry_arguments = list(entry)
            # the last item is a string entry
            add_string_argument(entry_arguments.pop())
            # the other items must not have arguments i.e. are booleans
            for item in entry_arguments:
                if item == 'h':
                    continue
                boolean_arguments.append(item)
        else:
            continue

    return {
        'booleans': boolean_arguments,
        'integers': [],
        'strings': string_arguments,
    }


def _minimist_from_getopt(prog, description, getopt_string, help_by_argument, name_by_argument):
    return minimist(prog, description, is_getopt=True,
                    help_by_argument=help_by_argument, name_by_argument=name_by_argument,
                    **_parse_getopt_string(getopt_string))


def break_apart_legacy_usage(value):
    lines = value.split('\n')
    line_parts = (line.split(':') for line in lines if line)
    return dict(((k.lstrip()[1:], v.strip()) for k, v in line_parts))


def parse_getopt_args(argv, getopt_string, prog="", description="", help_by_argument=_EMPTY_DICT, name_by_argument=_EMPTY_DICT):
    arg_parser = _minimist_from_getopt(
        prog, description, getopt_string,
        help_by_argument=help_by_argument, name_by_argument=name_by_argument)
    opts = arg_parser.parse_args(argv, namespace=GetoptCompatNamespace())
    try:
        args = getattr(opts, _POSITIONAL_MARKER)
    except AttributeError:
        args = []
    return (opts, args)
