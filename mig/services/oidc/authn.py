from idpyoidc.server.user_authn.user import UserPass


class MigUserPass(UserPass):
    def __init__(self, db, upstream_get=None):
        super(UserPass, self).__init__(upstream_get=upstream_get)
        self.user_db = db


def instantiate(*args, **kwargs):
    maybe_instance = kwargs.get('instance', None)
    assert isinstance(maybe_instance, MigUserPass)
    return maybe_instance
