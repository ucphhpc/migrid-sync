from oauthlib.oauth2 import WebApplicationServer

from mig.services.oidc.configured import ConfiguredServer
from mig.services.oidc.internals import OidcRequestValidator

def create_service(configuration):
    server, _ = _create_service(configuration)
    return server

def _create_service(configuration):
    request_validator = OidcRequestValidator(configuration)
    server = ConfiguredServer(request_validator)
    return (server, request_validator)
