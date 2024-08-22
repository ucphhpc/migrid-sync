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
                                ws_member_hosts, timeout=600):
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
    """

    assert isinstance(url, basestring)
    assert isinstance(define, basestring)
    assert isinstance(name, basestring)
    assert isinstance(member_hosts, list)
    assert isinstance(ws_member_hosts, list)
    assert isinstance(timeout, int)

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
        'referer_url': '%{' + name.upper() + "_PROXY_PROTOCOL}e://%{" + name.upper() + "_PROXY_FQDN}e/" + name + "/hub"
    }

    for host in member_hosts:
        fill_helpers['hosts'] += ''.join(['        ', host])

    for ws_host in ws_member_hosts:
        fill_helpers['ws_hosts'] += ''.join(['        ', ws_host])
    print("filling in jupyter gen_balancer_proxy_template with helper: (%s)" %
          fill_helpers)

    template = """
<IfDefine %(define)s>
    Header add Set-Cookie "%(route_cookie)s=%(balancer_worker_env)s; path=%(url)s" env=BALANCER_ROUTE_CHANGED
    SetEnvIf Host (.*) %(referer_fqdn)s

    ProxyTimeout %(timeout)s
    <Proxy balancer://%(name)s_hosts>
%(hosts)s
        ProxySet stickysession=%(route_cookie)s
    </Proxy>
    # Websocket cluster
    <Proxy balancer://ws_%(name)s_hosts>
%(ws_hosts)s
        ProxySet stickysession=%(route_cookie)s
    </Proxy>
    <Location %(url)s>
        ProxyPreserveHost on
        ProxyPass balancer://%(name)s_hosts%(url)s
        ProxyPassReverse balancer://%(name)s_hosts%(url)s
        RequestHeader set Remote-User %(remote_user_env)s
        RequestHeader set Referer %(referer_url)s
    </Location>
    <LocationMatch "%(url)s/(user/[^/]+)/(api/kernels/[^/]+/channels|terminals/websocket|api/events/subscribe)(/?|)">
        ProxyPass   balancer://ws_%(name)s_hosts
        ProxyPassReverse    balancer://ws_%(name)s_hosts
    </LocationMatch>
</IfDefine>""" % fill_helpers
    return template


def gen_openid_template(url, define, auth_type):
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
    print("filling in jupyter gen_openid_template with helper: (%s)" % fill_helpers)

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
