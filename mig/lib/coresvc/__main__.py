from argparse import ArgumentError
from getopt import getopt
import sys

from mig.shared.conf import get_configuration_object
from mig.services.coreapi.server import main as server_main


def _getopt_opts_to_options(opts):
    options = {}
    for k, v in opts:
        options[k[1:]] = v
    return options


def _required_argument_error(option, argument_name):
    raise ArgumentError(None, 'Missing required argument: %s %s' %
                        (option, argument_name.upper()))


if __name__ == '__main__':
    (opts, args) = getopt(sys.argv[1:], 'c:')
    opts_dict = _getopt_opts_to_options(opts)

    if 'c' not in opts_dict:
        raise _required_argument_error('-c', 'config_file')

    configuration = get_configuration_object(opts_dict['c'],
                                             skip_log=True, disable_auth_log=True)
    server_main(configuration)
