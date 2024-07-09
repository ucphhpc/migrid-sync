from cheroot.wsgi import WSGIServer
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from mig.wsgi import application_ as mig_application
from tests.support import MIG_BASE

_LOCAL_CONF_FILE = os.path.join(MIG_BASE, "envhelp/output/confs/MiGserver.conf")

def _noop(*args):
    pass

def application(environ, start_response):
    environ['SCRIPT_URI'] = environ['REQUEST_URI']

    return mig_application(environ, start_response, _config_file=_LOCAL_CONF_FILE, _skip_log=True)

def main():
    bind_addr = ('0.0.0.0', 8080)

    server = WSGIServer(bind_addr, application, numthreads=0)
    server.start()

if __name__ == '__main__':
    main()
