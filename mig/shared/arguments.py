import argparse
from collections import OrderedDict

from mig.shared.compat import PY2

_EMPTY_DICT = {}
_EMPTY_LIST = {}
_NO_DEFAULT = object()
_POSITIONAL_MARKER = '__args__'


class ArgumentBundleDefinition:
    def __init__(self, name, positional=_EMPTY_LIST):
        self._definition_name = name
        self._expected_positions = 0
        self._item_checks = []
        self._item_names = []

        if positional is not _EMPTY_LIST:
            self._define_positional(positional)

    @property
    def _fields(self):
        return self._item_names

    @property
    def _validators(self):
        return self._item_checks

    def __call__(self, *args):
        return self._extract_and_bundle(args, extract_by='position')

    def _define_positional(self, positional):
        for flag, name, validator_fn in positional:
            assert flag is None
            self._item_names.append(name)
            self._item_checks.append(validator_fn)
        self._expected_positions = len(positional)

    def _extract_and_bundle(self, args, extract_by=None):
        if extract_by == 'position':
            actual_positions = len(args)
            if actual_positions < self._expected_positions:
                raise ValueError('Error: too few arguments given (expected %d got %d)' % (
                    self._expected_positions, actual_positions))
            keys_to_bundle = list(range(actual_positions))
        elif extract_by == 'name':
            keys_to_bundle = self._item_names
        elif extract_by == 'short':
            keys_to_bundle = self._item_short
        else:
            raise RuntimeError()

        return ArgumentBundle.from_args(self, args, keys_to_bundle)

    def ensure_bundle(self, bundle_or_args):
        assert isinstance(self, ArgumentBundleDefinition)

        bundle_definition = self

        if isinstance(bundle_or_args, ArgumentBundle):
            assert bundle_or_args.name == bundle_definition._definition_name
            return bundle_or_args
        else:
            return bundle_definition(*bundle_or_args)


class ArgumentBundle(OrderedDict):
    def __init__(self, definition, dictionary):
        super(ArgumentBundle, self).__init__(dictionary)
        self._definition = definition

    @property
    def name(self):
        return self._definition._definition_name

    def __iter__(self):
        return iter(self.values())

    @classmethod
    def from_args(cls, definition, args, keys):
        dictionary = {key: args[key] for key in keys}
        return cls(definition, dictionary)


class GetoptCompatNamespace(argparse.Namespace):
    """Small glue abstraction to provide an object that when iterated yields
    tuples of cli-like options and their corresponding values thus emulating
    parsed getopt args."""

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
    if PY2:
        parser_options = {}
    else:
        parser_options = dict(allow_abbrev=False)
    parser = argparse.ArgumentParser(prog, **parser_options)

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
    """When supplied a MiG-style usage strings as used within the CLI tools
    return a dictionary of usage help descriptions keyed by their argument."""

    lines = value.split('\n')
    line_parts = (line.split(':') for line in lines if line)
    return dict(((k.lstrip()[1:], v.strip()) for k, v in line_parts))


def parse_getopt_args(argv, getopt_string, prog="", description="",
                      help_by_argument=_EMPTY_DICT,
                      name_by_argument=_EMPTY_DICT):
    """Parse a geptopt style usage string into an argparse-based argument
    parser. Handles positional and keyword arguments including optional
    display names and help strings."""

    arg_parser = _minimist_from_getopt(
        prog, description, getopt_string,
        help_by_argument=help_by_argument, name_by_argument=name_by_argument)
    opts = arg_parser.parse_args(argv, namespace=GetoptCompatNamespace())
    try:
        args = getattr(opts, _POSITIONAL_MARKER)
    except AttributeError:
        args = []
    return (opts, args)
