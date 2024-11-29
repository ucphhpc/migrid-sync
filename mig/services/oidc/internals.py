from flask import Flask
import json
import os
from urllib.parse import urlparse

from idpyoidc.configure import Configuration
from idpyoidc.server import Server
from idpyoidc.server.configure import OPConfiguration

from mig.services.oidc.authn import MigUserPass
from mig.services.oidc.userinfo import MigServiceOidcUserInfo
from mig.services.oidc.views import create_views_blueprint
from mig.shared.useradm import default_db_path
from mig.shared.userdb import load_user_db

dir_path = os.path.dirname(os.path.realpath(__file__))


def init_oidc_op(app):
    _op_config = app.srv_config

    server = Server(_op_config, cwd=dir_path)

    for endp in server.endpoint.values():
        p = urlparse(endp.endpoint_path)
        _vpath = p.path.split('/')
        if _vpath[0] == '':
            endp.vpath = _vpath[1:]
        else:
            endp.vpath = _vpath

    return server


def oidc_provider_init_app(op_config, name=None, **kwargs):
    name = name or __name__
    app = Flask(name, static_url_path='', **kwargs)
    app.srv_config = op_config

    oidc_op_views = create_views_blueprint()
    app.register_blueprint(oidc_op_views)

    # Initialize the oidc_provider after views to be able to set correct urls
    app.server = init_oidc_op(app)

    return app


# class PeerCertWSGIRequestHandler(werkzeug.serving.WSGIRequestHandler):
#     """
#     We subclass this class so that we can gain access to the connection
#     property. self.connection is the underlying client socket. When a TLS
#     connection is established, the underlying socket is an instance of
#     SSLSocket, which in turn exposes the getpeercert() method.
#
#     The output from that method is what we want to make available elsewhere
#     in the application.
#     """
#
#     def make_environ(self):
#         """
#         The superclass method develops the environ hash that eventually
#         forms part of the Flask request object.
#
#         We allow the superclass method to run first, then we insert the
#         peer certificate into the hash. That exposes it to us later in
#         the request variable that Flask provides
#         """
#         environ = super(PeerCertWSGIRequestHandler, self).make_environ()
#         x509_binary = self.connection.getpeercert(True)
#         if x509_binary:
#             x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, x509_binary)
#             environ['peercert'] = x509
#         else:
#             logger.warning('No peer certificate')
#             environ['peercert'] = ''
#         return environ


def _create_service(configuration):
    with open(os.path.join(dir_path, 'config.json')) as examplecfg:
        idpyoidc_cnf = json.loads(examplecfg.read())
    provider_config = Configuration(
                                     idpyoidc_cnf,
                                     entity_conf=[{
                                         "class": OPConfiguration, "attr": "op",
                                         "path": ["op", "server_info"]
                                     }],
                                     base_path=dir_path)

    db_path = default_db_path(configuration)
    user_db = load_user_db(db_path, do_lock=True)

    # user authn
    user_authn = MigUserPass(db=user_db)
    the_kwargs = provider_config.op.authentication['user']['kwargs']
    assert 'instance' in the_kwargs
    assert the_kwargs['instance'] is None
    the_kwargs['instance'] = user_authn

    # user info
    user_info = MigServiceOidcUserInfo(db=user_db)
    the_kwargs = provider_config.op.userinfo['kwargs']
    assert 'instance' in the_kwargs
    assert the_kwargs['instance'] is None
    the_kwargs['instance'] = user_info

    app = oidc_provider_init_app(provider_config.op, 'oidc_op')
    app.logger = configuration.logger

    return app, user_db, user_authn, user_info
