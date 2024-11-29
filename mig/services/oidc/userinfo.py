from idpyoidc.server.user_info import UserInfo

class MigServiceOidcUserInfo(UserInfo):
    pass


def instantiate(*args, **kwargs):
    maybe_instance = kwargs.get('instance', None)
    assert isinstance(maybe_instance, MigServiceOidcUserInfo)
    return maybe_instance
