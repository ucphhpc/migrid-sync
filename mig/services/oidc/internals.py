from types import SimpleNamespace

from oauthlib.oauth2 import WebApplicationServer
from oauthlib.openid import RequestValidator

from mig.shared.useradm import default_db_path, \
    search_users as useradm_search_users
from mig.shared.userdb import load_user_db


def create_model(**kwargs):
    if 'scopes' in kwargs:
        scopes = kwargs['scopes']
    elif isinstance(kwargs['scope'], str):
        scopes = list((kwargs['scope'],))
    else:
        scopes = kwargs['scope']

    return SimpleNamespace(
        scopes=scopes,
        distinguished_name=kwargs['distinguished_name'],
        client_id=kwargs['client_id'],
        response_type=kwargs['response_type'],
        redirect_uri=kwargs['redirect_uri'],
        authorization_code=kwargs.get('authorization_code', None),
    )


def search_users(configuration, search_filter):
    conf_path = configuration.config_file
    db_path = default_db_path(configuration)
    _, hits = useradm_search_users(search_filter, conf_path, db_path)
    return list((obj for _, obj in hits))


class OidcRequestValidator(RequestValidator):

    def __init__(self, configuration):
        self.configuration = configuration

        self._saved = {}

        db_path = default_db_path(configuration)
        self._user_db = load_user_db(db_path, do_lock=True)

    # Ordered roughly in order of appearance in the authorization grant flow

    def validate_client_id(self, client_id, request, *args, **kwargs):
        # Simple validity check, does client exist? Not banned?

        try:
            users = search_users(self.configuration, {
                'email': client_id
            })
            assert len(users) == 1
            return True
        except AssertionError:
            return False

    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        # Is the client allowed to use the supplied redirect_uri? i.e. has
        # the client previously registered this EXACT redirect uri.
        return True

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        # Is the client allowed to access the requested scopes?
        return len(scopes) == 1 and scopes[0] == 'openid'

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        # Scopes a client will authorize for if none are supplied in the
        # authorization request.
        return ['openid']

    def validate_response_type(self, client_id, response_type, client, request, *args, **kwargs):
        # Clients should only be allowed to use one type of response type, the
        # one associated with their one allowed grant type.
        # In this case it must be "code".
        return response_type == 'code'

    # Post-authorization

    def save_authorization_code(self, client_id, code, request, *args, **kwargs):
        # Remember to associate it with request.scopes, request.redirect_uri
        # request.client and request.user (the last is passed in
        # post_authorization credentials, i.e. { 'user': request.user}.
        users = search_users(self.configuration, {
            'email': client_id
        })
        assert len(users) == 1
        user = users[0]

        self._saved[client_id] = create_model(
            scopes=request.scopes,
            distinguished_name=user['distinguished_name'],
            **dict(request.uri_query_params)
        )
