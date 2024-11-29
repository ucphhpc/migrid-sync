from mig.services.oidc.internals import _create_service

def create_service(configuration):
    server, _ = _create_service(configuration)
    return server
