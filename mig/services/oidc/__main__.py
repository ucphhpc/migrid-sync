from oauthlib.oauth2 import WebApplicationServer

from mig.services.oidc.internals import OidcRequestValidator


def main():
    server = WebApplicationServer(OidcRequestValidator)


if __name__ == '__main__':
    main()
