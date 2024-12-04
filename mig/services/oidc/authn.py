from idpyoidc.server.user_authn.user import UserPass


class MigUserPass(UserPass):
    def __init__(self, db, *args, **kwargs):
        super(UserPass, self).__init__(*args, **kwargs)
        self.user_db = db

    def __call__(self, **kwargs):
        # Override the default behaviour which returns a tuple of (None, 200)
        # indicating it wishes to communicate success but the None trips up
        # checks within flask itself. Returning an empty string results in
        # responding the the client with a 200.

        return ''


def instantiate(*args, **kwargs):
    maybe_instance = kwargs.get('instance', None)
    assert isinstance(maybe_instance, MigUserPass)

    # set any kwargs supplied at the point where
    # pyoidc is wired to do instance instantiation
    apply_kwargs = kwargs.get('apply_kwargs', ())
    for apply_kwarg in apply_kwargs:
        setattr(maybe_instance, apply_kwarg, kwargs[apply_kwarg])

    return maybe_instance
