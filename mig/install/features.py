#!/usr/bin/env python3

import argparse
from collections import defaultdict
from configparser import ConfigParser
from enum import Enum
import os
import pip
import sys
from types import SimpleNamespace
from pip._internal.req.req_file import parse_requirements


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_MIG_BASE = os.path.normpath(os.path.join(_SCRIPT_DIR, '../..'))

sys.path.append(_LOCAL_MIG_BASE)

FEATURES_FILE = os.path.join(_LOCAL_MIG_BASE, 'FEATURES.ini')
FEATURES_REQUIREMENTS_DIR = os.path.join(_LOCAL_MIG_BASE, 'mig/install/requirements')
PIP_OVERRIDES = {
    'CLOUD': {
        'openstacksdk': 'OPENSTACKSDK_VERSION_OVERRIDE',
    },
    'MIGUX': {
        'migux': 'MIGUX_VERSION_OVERRIDE',
    },
}
_VERSIONCHARS = ('=', '<', '>')
_TRUTH_STRINGS = set(('True', 'true', 'yes', '1'))


def warn(msg=''):
    print(msg, file=sys.stderr)


class Features:
    """
    Instances of this object represent a set of named features and their state.
    """

    def __init__(self, interpretation_by_feature_name, overrides_supported):
        self.feature_names = sorted(interpretation_by_feature_name.keys())
        self._enabled_by_feature = {}
        self._requirements_by_feature = {}
        self._requirements_file_by_feature = {}
        self._overrides_by_feature = {}
        self._overrides_supported = overrides_supported

        for feature_name, interpretation in interpretation_by_feature_name.items():
            self._enabled_by_feature[feature_name] = interpretation.enabled
            self._requirements_by_feature[feature_name] = interpretation.requirements
            self._requirements_file_by_feature[feature_name] = interpretation.requirements_file

    def apply_enabled(self, enabled_by_feature_name):
        """
        Update the enabled state of features.
        """

        feature_keys = set(self.feature_names)
        present_keys = set(enabled_by_feature_name.keys())

        missing_feature_keys = feature_keys - present_keys
        if missing_feature_keys:
            raise RuntimeError("supplied feature state incomplete")

        self._enabled_by_feature = enabled_by_feature_name

    def apply_overrides(self, overrides_by_feature_name):
        """
        Update the overrides associated with features.
        """

        self._overrides_by_feature = overrides_by_feature_name

    def feature_is_enabled(self, feature_name):
        """
        Check if a named feature is enabled.
        """

        return self._enabled_by_feature[feature_name]

    def generate_pip_args(self):
        """
        Create pip arguments for each enabled feature.
        """

        per_package_args = []

        for feature_name in self.list_enabled_features():
            per_package_args.append(self.generate_pip_args_for_feature(feature_name))

        return per_package_args

    def generate_pip_args_for_feature(self, feature_name):
        """
        Create pip arguments for a particular feature.
        """

        overrides = self._overrides_by_feature.get(feature_name, None)

        if not overrides:
            # no overiddes detected therefore we can install
            # by simply using the requirements file as-is
            return ['-r', self._requirements_file_by_feature[feature_name]]

        package_args = []
        overridden_package_names = set(overrides.keys())

        # add the overridden packages
        for package_name in overridden_package_names:
            package_args.append(f"{package_name}=={overrides[package_name]}")

        # add the remaining packages based on the requirements file
        for entry in self._requirements_by_feature[feature_name]:
            package_name = Features._strip_version_if_present(entry.requirement)
            if package_name in overridden_package_names:
                continue
            package_args.append(entry.requirement)

        return package_args

    def list_enabled_features(self, return_as=list):
        """
        Return the names of features recorded as enabled.
        """

        return return_as((feature_name for feature_name in self.feature_names
                                        if self._enabled_by_feature[feature_name]))

    @staticmethod
    def _interpret_feature_definition(feature_name, feature_definition, requirements_dir):
        """
        Convert a named feature section within the features file to a
        structured intepretation suitable for consumption by the logic.
        """

        enabled = feature_definition.getboolean('default_on', fallback=False)
        has_requirements = feature_definition.getboolean('has_requirements', fallback=True)

        if has_requirements:
            requirements_file = os.path.join(requirements_dir, f"{feature_name.lower()}-requirements.txt")
            requirements = list(parse_requirements(requirements_file, session=None))
        else:
            requirements = []

        return SimpleNamespace(
            enabled=enabled,
            requirements=requirements,
            requirements_file=requirements_file,
        )

    @staticmethod
    def _strip_version_if_present(requirement):
        """
        Return only the name of a package given a requirement specifier.
        """

        for char in _VERSIONCHARS:
            index = requirement.find(char)
            if index == -1:
                continue
            return requirement[:index]
        return requirement

    @staticmethod
    def expand_definitions(definitions, requirements_dir):
        """
        Generate a dictionary of features names and a structured interpretation
        based on their definition in the main features file.
        """

        definitions_iterator = iter(definitions.items())
        next(definitions_iterator)  # skip default section

        return {feature_name: Features._interpret_feature_definition(feature_name,
                                                                     feature_definition,
                                                                     requirements_dir)
                for feature_name, feature_definition in definitions_iterator}

    @classmethod
    def from_definitions_file(cls, features_file, requirements_dir, overrides_supported={}):
        assert os.path.isabs(features_file)
        with open(features_file) as thefile:
            definitions = ConfigParser()
            definitions.read_file(thefile)
            return cls(Features.expand_definitions(definitions, requirements_dir), overrides_supported)

    @staticmethod
    def match_env_dict(features, env_dict):
        def enabled_or_fallback(feature_name):
            try:
                enable_string = env_dict[f"ENABLE_{feature_name.upper()}"]
                return enable_string in _TRUTH_STRINGS
            except KeyError:
                return features.feature_is_enabled(feature_name)

        enabled_by_feature_name = {}
        overrides_by_feature_name = defaultdict(dict)

        for feature_name in features.feature_names:
            enabled_by_feature_name[feature_name] = enabled_or_fallback(feature_name)

            env_override_flags = features._overrides_supported.get(feature_name, None)
            if not env_override_flags:
                continue

            for package_name, flag_name in env_override_flags.items():
                override_version = env_dict.get(flag_name, None)
                if not override_version:
                    continue
                overrides_by_feature_name[feature_name][package_name] = override_version

        return enabled_by_feature_name, overrides_by_feature_name

    @staticmethod
    def match_dotenv_file(features, dotenv_file):
        from dotenv import dotenv_values

        assert os.path.isabs(dotenv_file)
        dotenv_dict = dotenv_values(dotenv_file)

        return Features.match_env_dict(features, dotenv_dict)

    @staticmethod
    def match_configuration_file(features, configuration_file):
        from mig.shared.conf import get_configuration_object
        configuration = get_configuration_object(configuration_file, skip_log=True, disable_auth_log=True)

        def enabled_or_fallback(feature_name):
            try:
                return getattr(configuration, f"site_enable_{feature_name.lower()}")
            except AttributeError:
                return features.feature_is_enabled(feature_name)

        enabled_by_feature_name = {feature_name: enabled_or_fallback(feature_name)
                for feature_name in features.feature_names}
        return enabled_by_feature_name, {}


def main_enabled(features, args, print=print, warn=warn):
    if args.c:
        enabled_by_feature_name = Features.match_configuration_file(features, args.c)
        features.apply_enabled(enabled_by_feature_name)
    elif args.dotenv:
        enabled_by_feature_name, _ = Features.match_dotenv_file(features, args.dotenv)
        features.apply_enabled(enabled_by_feature_name)
    elif args.env:
        enabled_by_feature_name, overrides_by_feature_name = Features.match_env_dict(features, args.env)
        features.apply_enabled(enabled_by_feature_name)
    else:
        warn("no feature coniguration available; showing those enabled by default only")
    print(f"enabled features: {', '.join(features.list_enabled_features())}")

    return 0


def main_install(features, args, print=print, warn=warn):
    if args.c:
        enabled_by_feature_name = Features.match_configuration_file(features, args.c)
        features.apply_enabled(enabled_by_feature_name)
    elif args.dotenv:
        enabled_by_feature_name, overrides_by_feature_name = Features.match_dotenv_file(features, args.dotenv)
        features.apply_enabled(enabled_by_feature_name)
    elif args.env:
        enabled_by_feature_name, overrides_by_feature_name = Features.match_env_dict(features, args.env)
        features.apply_enabled(enabled_by_feature_name)
        features.apply_overrides(overrides_by_feature_name)
    else:
        warn("no feature coniguration available; showing those enabled by default only")
        warn()

    all_pip_args = features.generate_pip_args()

    if args.check:
        for pip_args in all_pip_args:
            print(f"pip install {' '.join(pip_args)}")
        return

    raise NotImplementedError("install is not currently implemented")


def main_show(features, args, print=print, warn=warn):
    print(f"available features: {', '.join(features.feature_names)}")


_COMMAND_HANDLERS = dict(
    enabled=main_enabled,
    install=main_install,
    show=main_show,
)


def main(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    show_command = subparsers.add_parser('show')

    enabled_command = subparsers.add_parser('enabled')
    enabled_command.add_argument('-c', default=None)
    enabled_command.add_argument('--dotenv', default=None, type=os.path.abspath)
    enabled_command.add_argument('--env', action='store_const', const=os.environ)

    install_command = subparsers.add_parser('install')
    install_command.add_argument('-c', default=None)
    install_command.add_argument('--check', action='store_true', default=False)
    install_command.add_argument('--dotenv', default=None, type=os.path.abspath)
    install_command.add_argument('--env', action='store_const', const=os.environ)

    args = parser.parse_args(args=argv)

    if not args.command:
        parser.print_usage()
        return 0

    return args_main(parser.parse_args(args=argv))

def args_main(args, *, print=print, warn=warn, features=None):
    features = features or Features.from_definitions_file(
        FEATURES_FILE,
        FEATURES_REQUIREMENTS_DIR,
        PIP_OVERRIDES,
    )

    command_handler = _COMMAND_HANDLERS[args.command]
    try:
        command_handler(features, args, print=print, warn=warn)
        return 0
    except Exception as exc:
        warn(exc)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
