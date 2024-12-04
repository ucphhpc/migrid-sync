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
from mig.shared.useradm import default_db_path, \
    search_users as useradm_search_users
from mig.shared.userdb import load_user_db

_EMPTY_DICT = {}
dir_path = os.path.dirname(os.path.realpath(__file__))


def init_oidc_op(app, **kwargs):
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


def oidc_provider_init_app(op_config, name=None, client_db=None, **kwargs):
    name = name or __name__
    app = Flask(name, root_path=dir_path, **kwargs)
    app.srv_config = op_config

    oidc_op_views, oidc_op_views_state = create_views_blueprint()
    app.register_blueprint(oidc_op_views)

    # Initialize the oidc_provider after views to be able to set correct urls
    app.server = init_oidc_op(app, client_db=client_db)

    return app, oidc_op_views_state


def oidc_state_user_record(client_id):
    return {
        'client_secret': '__PASSWORD__',
        'redirect_uris': ['http://back.to/me'],
    }


class OidcState:
    def __init__(self, configuration, user_db):
        self._configuration = configuration
        self._passwords = None
        self._user_db = user_db
        self._user_db_values = list(user_db.values())

        self._passwords = {client['email']:oidc_state_user_record(client['email']) for client in self._user_db_values}

    def __getitem__(self, item):
        return self._passwords.get(item, _EMPTY_DICT)

    # quack like a dict
    def get(self, item, *args):
        return self.__getitem__(item)

    def get_user_client_id(self, client_id):
        search_filter = {
            'email': client_id,
        }
        _, users = useradm_search_users(search_filter, None, None, configuration=self._configuration)
        users_count = len(users)
        if users_count == 0:
            raise NotImplementedError('NOT_FOUND')
        if users_count > 1:
            raise NotImplementedError('BAD_SEARCH')
        else:
            return users[0]


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


def _create_service(configuration, debug=False):
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
    oidc_state = OidcState(configuration, user_db)

    the_kwargs = provider_config.op['client_db']['kwargs']
    assert 'instance' in the_kwargs
    assert the_kwargs['instance'] is None
    the_kwargs['instance'] = oidc_state

    # user authn
    user_authn = MigUserPass(db=user_db)
    the_kwargs = provider_config.op.authentication['user']['kwargs']
    assert 'instance' in the_kwargs
    assert the_kwargs['instance'] is None
    the_kwargs['instance'] = user_authn
    the_kwargs['apply_kwargs'] = ['upstream_get']

    # user info
    user_info = MigServiceOidcUserInfo(db=user_db)
    the_kwargs = provider_config.op.userinfo['kwargs']
    assert 'instance' in the_kwargs
    assert the_kwargs['instance'] is None
    the_kwargs['instance'] = user_info

    app, views_state = oidc_provider_init_app(provider_config.op, 'oidc_op', client_db=oidc_state)
    app.debug = debug
    app.logger = configuration.logger

    oidc_state.views = views_state

    def _mig_service_oidc_get_client_info(clientid, endpoint):
        user = oidc_state.get_user_client_id(clientid)
        return { 'client_authn_method': ['client_secret_basic'] }
    oidc_state.views.authz['get_client_info'] = _mig_service_oidc_get_client_info

    return app, oidc_state, user_authn, user_info
