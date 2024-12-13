from argparse import ArgumentError
import sys

from mig.shared.arguments import parse_getopt_args
from mig.shared.conf import get_configuration_object
from mig.services.coreapi.server import main as server_main


def _required_argument_error(option, argument_name):
    raise ArgumentError('Missing required argument: %s %s' %
                        (option, argument_name.upper()))


if __name__ == '__main__':
    (opts, args) = parse_getopt_args(sys.argv[1:], 'c:')

    if 'c' not in opts:
        raise _required_argument_error('-c', 'config_file')

    configuration = get_configuration_object(opts.c)
    server_main(configuration)
