import sys

from mig.shared.arguments import parse_getopt_args
from mig.shared.conf import get_configuration_object
from mig.services.oidc import create_service


def _required_option_error(option_argument, option_name):
    return ValueError('Missing required option %s %s' % (option_argument, option_name.upper()))


def main(args):
    configuration = get_configuration_object(args.config_file)
    service = create_service(configuration)


if __name__ == '__main__':
    (opts, args) = parse_getopt_args(sys.argv[1:], 'c:')

    if 'c' not in opts:
        raise _required_option_error('-c', 'config_file')

    configuration = get_configuration_object(opts.c)
    service = create_service(configuration)
