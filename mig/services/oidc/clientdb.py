from mig.services.oidc.internals import OidcState


def instantiate(*args, **kwargs):
    maybe_instance = kwargs.get('instance', None)
    assert isinstance(maybe_instance, OidcState)
    return maybe_instance
