#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jupyter - Helper functions for the jupyter service
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

""" Jupyter service helper functions """

from __future__ import print_function
from __future__ import absolute_import
from past.builtins import basestring


def gen_balancer_proxy_template(url, define, name, member_hosts,
                                ws_member_hosts,
                                timeout=600,
                                enable_proxy_https=True,
                                proxy_balancer_template_kwargs=None):
    """ Generates an apache proxy balancer configuration section template
     for a particular jupyter service. Relies on the
     https://httpd.apache.org/docs/2.4/mod/mod_proxy_balancer.html module to
     generate the balancer proxy configuration.
    url: Setting the url_path to where the jupyter service is to be located.
    define: The name of the apache variable containing the 'url' value.
    name: The name of the jupyter service in question.
    member_hosts: The list of unique identifiers that should be used to fill
     in balancer member defitions.
    ws_member_hosts: The list of unique identifiers that should be used to fill
     in websocket balancer member defitions.
    timeout: The proxy timeout in seconds.
    enable_proxy_https: Whether or not to enable SSL/TLS proxying.
    proxy_balancer_template_kwargs: The optional extra apache config options that is used to
     generate the proxy balancer templates. This for instance can be used to pass SSL options
    such as a custom self-signed CA that should be used to establish a
    trusted SSL/TLS connection to the designated jupyter service.
    An example of this could be {'SSLProxyCACertificateFile': 'path/to/local/ca-certificate.pem'}.
    """

    if not proxy_balancer_template_kwargs:
        proxy_balancer_template_kwargs = {}

    assert isinstance(url, basestring)
    assert isinstance(define, basestring)
    assert isinstance(name, basestring)
    assert isinstance(member_hosts, list)
    assert isinstance(ws_member_hosts, list)
    assert isinstance(timeout, int)
    assert isinstance(enable_proxy_https, bool)
    assert isinstance(proxy_balancer_template_kwargs, dict)

    fill_helpers = {
        'url': url,
        'define': define,
        'name': name,
        'route_cookie': name.upper() + "_ROUTE_ID",
        'balancer_worker_env': '.%{BALANCER_WORKER_ROUTE}e',
        'remote_user_env': '%{PROXY_USER}e',
        'hosts': '',
        'ws_hosts': '',
        'timeout': timeout,
        'referer_fqdn': name.upper() + "_PROXY_FQDN=$1",
        'referer_url': '%{' + name.upper() + "_PROXY_PROTOCOL}e://%{" + name.upper() + "_PROXY_FQDN}e/" + name + "/hub",
        'proxy_balancer_template': ''
    }

    for host in member_hosts:
        fill_helpers['hosts'] += ''.join(['        ', host])

    for ws_host in ws_member_hosts:
        fill_helpers['ws_hosts'] += ''.join(['        ', ws_host])

    proxy_balancer_template = ""
    if enable_proxy_https:
        ssl_proxy_template_options = {}
        if "SSLProxyVerify" not in proxy_balancer_template_kwargs:
            ssl_proxy_template_options["SSLProxyVerify"] = "require"
        if "SSLProxyCheckPeerCN" not in proxy_balancer_template_kwargs:
            ssl_proxy_template_options["SSLProxyCheckPeerCN"] = "on"
        if "SSLProxyCheckPeerName" not in proxy_balancer_template_kwargs:
            ssl_proxy_template_options["SSLProxyCheckPeerName"] = "on"
        for key, value in proxy_balancer_template_kwargs.items():
            ssl_proxy_template_options[key] = value

        for key, value in ssl_proxy_template_options.items():
            proxy_balancer_template += "%s %s\n" % (key, value)

    fill_helpers["proxy_balancer_template"] = proxy_balancer_template

    template = """
<IfDefine %(define)s>
    Header add Set-Cookie "%(route_cookie)s=%(balancer_worker_env)s; path=%(url)s" env=BALANCER_ROUTE_CHANGED

    ProxyTimeout %(timeout)s
    <Proxy balancer://%(name)s_hosts>
        %(proxy_balancer_template)s
%(hosts)s
        ProxySet stickysession=%(route_cookie)s
    </Proxy>
    # Websocket cluster
    <Proxy balancer://ws_%(name)s_hosts>
        %(proxy_balancer_template)s
%(ws_hosts)s
        ProxySet stickysession=%(route_cookie)s
    </Proxy>
    <Location %(url)s>
        ProxyPass balancer://%(name)s_hosts%(url)s
        ProxyPassReverse balancer://%(name)s_hosts%(url)s
        RequestHeader set Remote-User %(remote_user_env)s
        RequestHeader set "X-Forwarded-Proto" expr=%%{REQUEST_SCHEME}
    </Location>
    <LocationMatch "%(url)s/(user/[^/]+)/(api/kernels/[^/]+/channels|terminals/websocket|api/events/subscribe)(/?|)">
        ProxyPass   balancer://ws_%(name)s_hosts
        ProxyPassReverse    balancer://ws_%(name)s_hosts
    </LocationMatch>
</IfDefine>""" % fill_helpers

    return template


def gen_openid_template(url, define, auth_type, _print=print):
    """Generates an openid 2.0 or connect apache configuration section template
    for a particular jupyter service.
    url: Setting the url_path to where the jupyter service is to be located.
    define: The name of the apache variable containing the 'url' value.
    auth_type: the apache AuthType for this section (OpenID or openid-connect).
    """

    assert isinstance(url, basestring)
    assert isinstance(define, basestring)
    assert isinstance(auth_type, basestring)
    assert auth_type in ("OpenID", "openid-connect")

    fill_helpers = {
        'url': url,
        'define': define,
        'auth_type': auth_type
    }
    _print("filling in jupyter gen_openid_template with helper: (%s)" % fill_helpers)

    template = """
<IfDefine %(define)s>
    <Location %(url)s>
        # Pass SSL variables on
        SSLOptions +StdEnvVars
        AuthType %(auth_type)s
        require valid-user
    </Location>
</IfDefine>
""" % fill_helpers
    return template


def gen_rewrite_template(url, define, name):
    """ Generates an rewrite apache configuration section template
     for a particular jupyter service.
    url: Setting the url_path to where the jupyter service is to be located.
    define: The name of the apache variable containing the 'url' value.
    name: The name of the jupyter service in question.
    """

    assert isinstance(url, basestring)
    assert isinstance(define, basestring)
    assert isinstance(name, basestring)

    fill_helpers = {
        'url': url,
        'define': define,
        'auth_phase_user': '%{LA-U:REMOTE_USER}',
        'referer_protocol_env_variable': name.upper() + "_PROXY_PROTOCOL",
        'uri': '%{REQUEST_URI}',
        'scheme': '%{REQUEST_SCHEME}'
    }
    print("filling in jupyter gen_rewrite_template with helper: (%s)" % fill_helpers)

    template = """
<IfDefine %(define)s>
    <Location %(url)s>
        RewriteCond %(auth_phase_user)s !^$
        RewriteRule .* - [E=PROXY_USER:%(auth_phase_user)s,NS]

        RewriteCond %(scheme)s !^$
        RewriteRule .* - [E=%(referer_protocol_env_variable)s:%(scheme)s,NS]
    </Location>
    RewriteCond %(uri)s ^%(url)s
    RewriteRule ^ - [L]
</IfDefine>
""" % fill_helpers
    return template
