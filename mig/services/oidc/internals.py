from oauthlib.oauth2 import WebApplicationServer
from oauthlib.openid import RequestValidator

from mig.shared.useradm import default_db_path
from mig.shared.userdb import load_user_db


class OidcRequestValidator(RequestValidator):

    def __init__(self, configuration):
        self.configuration = configuration

        db_path = default_db_path(configuration)
        self._user_db = load_user_db(db_path, do_lock=True)

    # Ordered roughly in order of appearance in the authorization grant flow

    def validate_client_id(self, client_id, request, *args, **kwargs):
        # Simple validity check, does client exist? Not banned?

        return False
