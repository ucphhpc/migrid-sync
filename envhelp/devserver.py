from cheroot import wsgi
import codecs
import importlib
import io
import os
import sys

from mig.shared.compat import PY2
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import MIG_BASE, MIG_ENV


_MIG_CODE = os.path.join(MIG_BASE, "mig")
_LOCAL_CONF = None


if MIG_ENV != 'local':
    pass
else:
    # force testconfig as the conig file path
    is_py2 = PY2
    _conf_dir_suffix = "-py%s" % ('2' if is_py2 else '3',)
    _conf_dir = "testconfs%s" % (_conf_dir_suffix,)
    _LOCAL_CONF = os.path.join(
        MIG_BASE, 'envhelp/output', _conf_dir, 'MiGserver.conf')
assert _LOCAL_CONF is not None


# workaround for migwsgi being placed witin a non-module directory
def _import_migwsgi():
    sys.path.append(os.path.join(MIG_BASE, 'mig/wsgi-bin'))
    migwsgi = importlib.import_module('migwsgi')
    sys.path.pop(-1)
    return migwsgi
migwsgi = _import_migwsgi()
mig_application = migwsgi.application_


_MIME_BY_EXTENSION = {
    ".css": "text/css",
    ".js": "application/javascript",
}


def _mime_for_file_name(file_name):
    _, path_ext = os.path.splitext(file_name)
    return _MIME_BY_EXTENSION.get(path_ext, 'application/octet-stream')


def _serve_dir(*subdir_parts):
    def serve(relative_file_parts):
        mime_type = _mime_for_file_name(relative_file_parts[-1])
        file_path = os.path.join(MIG_BASE, *subdir_parts, *relative_file_parts)
        with io.open(file_path, 'rb') as f:
            return (mime_type, f.readlines())

    return serve


def _serve_static(value):
    def serve(relative_file_parts):
        return ("text/html", [codecs.encode(relative_file_parts[-1], 'utf8')])
    return serve


_SERVE_STATIC_BY_DIR = {
    "assets": _serve_dir("mig/assets"),
    "images": _serve_dir("mig/images"),
    "public": _serve_static("state/wwwpublic"),
}


def application(environ, start_response):
    path_parts = environ['PATH_INFO'].split('/')[1:]

    if path_parts and path_parts[0] in _SERVE_STATIC_BY_DIR:
        topdir, *relative_file_parts = path_parts
        serve_static = _SERVE_STATIC_BY_DIR[topdir]
        content_type, content_data = serve_static(relative_file_parts)
        start_response('200 OK', [('Content-Type', content_type)])
        return content_data

    environ['MIG_CONF'] = _LOCAL_CONF
    environ['SCRIPT_URI'] = ''.join(('http://', environ['HTTP_HOST'], environ['PATH_INFO']))

    configuration = get_configuration_object(_LOCAL_CONF, skip_log=True, disable_auth_log=True)

    return mig_application(configuration, environ, start_response)

def main():
    bind_addr = ('0.0.0.0', 8080)

    server = wsgi.Server(bind_addr, application, numthreads=1)
    try:
        print("starting devserver..")
        server.start()
    except KeyboardInterrupt:
        print("stopping devserver..")
        server.stop()

if __name__ == '__main__':
    main()
