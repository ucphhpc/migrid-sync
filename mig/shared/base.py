#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - shared base helper functions
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""Base helper functions"""

from __future__ import print_function
from __future__ import absolute_import
from past.builtins import basestring

import base64
import os
import re

# IMPORTANT: do not import any other MiG modules here - to avoid import loops
from mig.shared.defaults import default_str_coding, default_fs_coding, \
    keyword_all, keyword_auto, sandbox_names, _user_invisible_files, \
    _user_invisible_dirs, _vgrid_xgi_scripts, cert_field_order, csrf_field, \
    gdp_distinguished_field, valid_gdp_auth_scripts, valid_gdp_anon_scripts, \
    STR_KIND, FS_KIND, AUTH_OPENID_V2, AUTH_OPENID_CONNECT, AUTH_CERTIFICATE, \
    X509_USER_ID_FORMAT, UUID_USER_ID_FORMAT

_id_sep, _dir_sep, _id_space, _dir_space = '/', '+', ' ', '_'
_key_val_sep = '='
_remap_fields = ['CN', 'O', 'OU']
cert_field_map = dict(cert_field_order)


def get_site_base_url(configuration):
    """Lookup main site URL with preference for HTTPS if available"""
    main_url = configuration.migserver_http_url
    if configuration.migserver_https_url:
        main_url = configuration.migserver_https_url
    return main_url


def client_id_dir(client_id):
    """Map client ID to a valid directory name:
    client_id is a distinguished name on the form /X=ab/Y=cdef ghi/Z=klmn...
    so we just replace slashes with plus signs and space with underscore
    for the name fields. Please note that e.g. emailAddress may contain
    underscore, which must be preserved.
    """

    dir_parts = []
    for entry in client_id.split(_id_sep):
        if entry.split(_key_val_sep, 1)[0] in _remap_fields:
            entry = entry.replace(_id_space, _dir_space)
        dir_parts.append(entry)
    client_dir = _dir_sep.join(dir_parts)
    return client_dir


def client_dir_id(client_dir):
    """Map client directory name to valid client ID:
    client_dir is a distinguished name on the form +X=ab+Y=cdef_ghi+Z=klmn...
    so we just replace slashes with plus signs and space with underscore
    for the name fields. Please note that e.g. emailAddress may contain
    underscore, which must be preserved.
    """

    id_parts = []
    for entry in client_dir.split(_dir_sep):
        if entry.split(_key_val_sep, 1)[0] in _remap_fields:
            entry = entry.replace(_dir_space, _id_space)
        id_parts.append(entry)
    client_id = _id_sep.join(id_parts)
    return client_id


def client_alias(client_id):
    """Map client ID to a version containing only simple ASCII characters.
    This is for e.g. commandline friendly use and it is a one-to-one mapping.
    """
    # sftp and friends choke on potential '=' padding - replace by underscore
    return base64.urlsafe_b64encode(client_id).replace('=', '_')


def mask_creds(user_dict, mask_fields=[csrf_field, 'reset_token', 'password',
                                       'old_password', 'password_hash',
                                       'old_password_hash', 'password_digest',
                                       'password_encrypted', 'verifypassword',
                                       'transfer_pw'],
               masked_value='**HIDDEN**', subst_map={}):
    """Returns a copy of user_dict with any password fields from mask_fields
    list replaced by masked_value string. The optional subst_map dictionary
    maps field names to substitution patterns for the re.sub() function to
    transform the existing value in user_dict into a filtered one. E.g. to mask
    out inlined credentials.
    """
    masked = user_dict.copy()
    for mask_field in mask_fields:
        if masked.get(mask_field, ''):
            masked[mask_field] = masked_value
    for (target, pattern_pair) in subst_map.items():
        if masked.get(target, ''):
            masked[target] = re.sub(pattern_pair[0], pattern_pair[1],
                                    masked[target])
    return masked


def expand_openid_alias(alias_id, configuration):
    """Expand openid alias to full certificate DN from symlink"""
    home_path = os.path.join(configuration.user_home, alias_id)
    if os.path.islink(home_path):
        real_home = os.path.realpath(home_path)
        client_dir = os.path.basename(real_home)
        client_id = client_dir_id(client_dir)
    else:
        client_id = alias_id
    return client_id


def get_short_id(configuration, user_id, user_alias):
    """Internal helper to translate user_id and user_alias to short_id"""
    short_id = extract_field(user_id, user_alias)

    if configuration.site_enable_gdp:

        # TODO add 'user_gdp_alias' to configuration ?

        gdp_id = extract_field(user_id, gdp_distinguished_field)
        if gdp_id is not None:
            short_id = "%s@%s" % (short_id, gdp_id)

    return short_id


def get_user_id(configuration, user):
    """Extract configured unique user ID value from user dictionary. The actual
    chosen value depends on the user_id_format from the site configuration and
    can be X509 or UUID of user.
    """
    user_id = None
    uid_format = configuration.site_user_id_format
    if uid_format == X509_USER_ID_FORMAT:
        user_id = user.get('distinguished_name', None)
    elif uid_format == UUID_USER_ID_FORMAT:
        user_id = user.get('unique_id', None)
    else:
        raise ValueError("invalid user ID format %s" % uid_format)
    if user_id is None:
        raise ValueError("no client ID found for %s in %s" %
                         (uid_format, user))
    return user_id


def get_client_id(user):
    """Extract client ID on the Distinguished Name form from user dictionary.
    Please note that this is used for all public and human-friendly display,
    whereas user_id may be a generated random key UUID or coincide with DN
    depending on the actual site configuration.
    """
    client_id = user.get('distinguished_name', None)
    if client_id is None:
        raise ValueError("no client DN found in %s" % user)
    return client_id


# TODO: migrate all uses of binascii hexlify to use this helper instead
def hexlify(strval):
    """Convert strval to hexadecimal with only lower case letters"""
    return base64.b16encode(strval).lower()


# TODO: migrate all uses of binascii unhexlify to use this helper instead
def unhexlify(hexval):
    """Convert possibly lowercase hexlified hexval back to str"""
    # IMPORTANT: base16decode requires uppercase string
    return base64.b16decode(hexval.upper())


def is_gdp_user(configuration, client_id):
    """Helper to distinguish GDP project users from top-level users"""
    if client_id.split(_id_sep)[-1].startswith(gdp_distinguished_field):
        return True
    else:
        return False


def fill_user(target):
    """Fill target user dictionary with all expected fields"""

    for (key, _) in cert_field_order:
        target[key] = target.get(key, '')
    return target


def fill_distinguished_name(user):
    """Fill distinguished_name field from other fields if not already set.

    Please note that MiG certificates get empty fields set to NA, so this
    is translated here, too.
    """

    if user.get('distinguished_name', ''):
        return user
    else:
        user['distinguished_name'] = ''
    for (key, val) in cert_field_order:
        setting = user.get(key, '')
        if not setting:
            setting = 'NA'
        user['distinguished_name'] += '/%s=%s' % (val, setting)

    setting = user.get(gdp_distinguished_field, '')
    if setting:
        user['distinguished_name'] += '/%s=%s' \
            % (gdp_distinguished_field, setting)

    return user


def distinguished_name_to_user(distinguished_name):
    """Build user dictionary from distinguished_name string on the form:
    /X=abc/Y=def/Z=ghi

    Please note that MiG certificates get empty fields set to NA, so this
    is translated back here, too.
    """

    user_dict = {'distinguished_name': distinguished_name}
    parts = distinguished_name.split(_id_sep)
    for field in parts:
        if not field or field.find(_key_val_sep) == -1:
            continue
        (key, val) = field.split(_key_val_sep, 1)
        if 'NA' == val:
            val = ''
        if not key in cert_field_map.values():
            user_dict[key] = val
        else:
            for (name, short) in cert_field_order:
                if key == short:
                    user_dict[name] = val
    return user_dict


def extract_field(distinguished_name, field_name):
    """Extract field_name value from client_id if included"""
    user = distinguished_name_to_user(distinguished_name)
    return user.get(field_name, None)


def pretty_format_user(distinguished_name, hide_email=True):
    """Format distinguished_name of a user to a human-friendly display format,
    and optionally include the email address.
    """
    user_dict = {'full_name': '', 'organization': '', 'email': ''}
    user_dict.update(distinguished_name_to_user(distinguished_name))
    if hide_email:
        user_dict['email'] = 'email hidden'
    else:
        # NOTE: obfuscate email by replacing with html entities
        for (src, dst) in [('@', '&#064;'), ('.', '&#046;')]:
            user_dict['email'] = user_dict.get('email', '').replace(src, dst)
    return "%(full_name)s, %(organization)s &lt;%(email)s&gt;" % user_dict


def canonical_user(configuration, user_dict, limit_fields):
    """Apply basic transformations to user dicts for consistency. Remove
    unexpected fields, lower-case email, capitalize full name and uppercase
    country and state.
    """
    canonical = {}
    for (key, val) in user_dict.items():
        if not key in limit_fields:
            continue
        if isinstance(val, basestring):
            val = val.strip()
        if key == 'full_name':
            # IMPORTANT: we get utf8 coded bytes here and title() treats such
            # chars as word termination. Temporarily force to unicode.
            val = force_utf8(force_unicode(val).title())
        elif key == 'email':
            val = val.lower()
        elif key == 'country':
            val = val.upper()
        elif key == 'state':
            val = val.upper()
        canonical[key] = val
    return canonical


def canonical_user_with_peers(configuration, user_dict, limit_fields):
    """Extended version of canonical_user to additionally extract any saved
    peers fields in user_dict on a canonical form.
    """
    canonical = canonical_user(configuration, user_dict, limit_fields)
    legacy_peers = user_dict.get('peers', [])
    for explicit_field in configuration.site_peers_explicit_fields:
        peers_field = "peers_%s" % explicit_field
        current_val = user_dict.get(peers_field, '')
        if not current_val and legacy_peers:
            current_val = ', '.join([extract_field(i, explicit_field) for i
                                     in legacy_peers])
        if current_val:
            canonical[peers_field] = current_val
    return canonical


def sandbox_resource(unique_resource_name):
    """Returns boolean indicating if the resource is a sandbox"""
    fqdn = unique_resource_name.rsplit('.', 1)[0]
    return fqdn in sandbox_names


def invisible_file(filename):
    """Returns boolean indicating if the file with filename is among restricted
    files to completely hide. Such files can not safely be removed or modified
    by users and should only be changed through fixed interfaces.
    Provided filename is expected to be without directory prefix.
    """
    return filename in _user_invisible_files


def invisible_dir(dir_path):
    """Returns boolean indicating if the directory with dir_path is among
    restricted directories to completely hide. Such directories can not
    safely be removed or modified by users and should only be changed
    through fixed interfaces.
    Provided dir_path can contain a directory prefix.
    """
    for dirname in dir_path.split(os.sep):
        if dirname in _user_invisible_dirs:
            return True
    return False


def invisible_path(path, allow_vgrid_scripts=False):
    """Returns boolean indicating if the file or directory with path is among
    restricted files or directories to completely hide. Such items can not
    safely be removed or modified by users and should only be changed through
    a few restricted interfaces.
    Provided path may be absolute or relative.
    The optional allow_vgrid_scripts argument can be set to allow certain Xgi
    script paths inside otherwise invisible directories. This is useful in
    relation to specifically allowing access to vgrid collaboration component
    Xgi scripts from apache.
    Please note that users should NEVER be allowed write access to those, as it
    would open up a major remote code execution security hole!
    Thus, only use allow_vgrid_scripts when checking access to files in apache
    chroot checks.
    """
    filename = os.path.basename(path)
    if invisible_file(filename):
        return True
    elif invisible_dir(path):
        if allow_vgrid_scripts:
            for i in _vgrid_xgi_scripts:
                # NOTE: mercurial uses hgweb.cgi/BLA to pass args,
                #       so path.endswith(i) is too narrow
                if path.find(i) != -1:
                    return False
        # No valid exception
        return True
    return False


def requested_backend(environ=None, fallback='UNKNOWN', strip_ext=True):
    """Lookup requested backend name from environ or os.environ if not provided.
    Return backend without any filename exension unless strip_ext is disabled
    and use fallback value if no backend was found in environ.

    IMPORTANT: this version assures that the value is safe for page output,
    too, so use it whenever the actual (potentially unsafe) URL is not a strict
    requirement.
    """
    if not environ:
        environ = os.environ
    # NOTE: RPC wrappers inject name of actual backend as BACKEND_NAME
    # NOTE: wsgi sets SCRIPT_X to wsgi-bin but PATH_TRANSLATED contains backend
    # IMPORTANT: use only filtered values like SCRIPT_NAME and SCRIPT_FILENAME
    #            as Apache strips e.g. unsafe injected URL values like
    #            cgi-sid/BACKEND.py/UNSAFECONTENT?VALIDQUERY

    script_path = environ.get('BACKEND_NAME', False) or \
        environ.get('PATH_TRANSLATED', False) or \
        environ.get('SCRIPT_NAME', False) or \
        environ.get('SCRIPT_FILENAME', fallback)
    backend_name = os.path.basename(script_path)
    if strip_ext:
        backend_name = os.path.splitext(backend_name)[0]
    # NOTE: for extra safety we always filter all but simple chars
    return re.sub(r'[^a-zA-Z0-9._-]+', '', backend_name)


def requested_page(environ=None, fallback='home.py', name_only=False,
                   strip_ext=False, include_unsafe=False):
    """Lookup requested page from environ or os.environ if not provided.
    Return fallback if no page was found in environ. Return only the script_name
    If the include_unsafe arg is set the lookup includes potentially unsafe
    environment values without proper filtering and then MUST be used very
    carefully, because printing may otherwise result in XSS vulnerabilities.
    """
    if not environ:
        environ = os.environ
    if name_only:
        return requested_backend(environ, fallback, strip_ext)
    # NOTE: RPC wrappers inject name of actual backend as BACKEND_NAME
    # IMPORTANT: the remaining vars MAY contain raw user-provided content like
    #            cgi-sid/BACKEND.py/UNSAFECONTENT?VALIDQUERY
    #            Please use the result with maximum care!
    page_path = environ.get('BACKEND_NAME', False) or \
        environ.get('SCRIPT_URL', False) or \
        environ.get('SCRIPT_URI', False) or \
        environ.get('PATH_INFO', False) or \
        environ.get('REQUEST_URI', fallback)
    # Strip any query args
    page_path = page_path.split('?', 1)[0]
    if strip_ext:
        page_path = os.path.splitext(page_path)[0]
    if include_unsafe:
        return page_path
    else:
        # NOTE: for safety we filter all but simple URL chars
        return re.sub(r'[^a-zA-Z0-9:/._-]+', '', page_path)


def requested_url_base(environ=None, include_unsafe=False, uri_field='SCRIPT_URI'):
    """Lookup requested url base from environ or os.environ if not provided.
    If the include_unsafe arg is set the result includes potentially unsafe
    values without proper filtering and thus MUST be used very carefully,
    because printing may otherwise result in XSS vulnerabilities.
    """
    if not environ:
        environ = os.environ
    full_url = environ.get(uri_field, None)
    parts = full_url.split('/', 3)
    url_base = '/'.join(parts[:3])
    if include_unsafe:
        return url_base
    else:
        # NOTE: for safety we filter all but simple URL chars
        return re.sub(r'[^a-zA-Z0-9/:._-]+', '', url_base)


def verify_local_url(configuration, req_url):
    """Check that provided req_url is really hosted locally at this site to
    e.g. prevent unvalidated redirects or forwards from crafted URLs. Extracts
    the requested URL base and checks it is among the configured local site
    addresses.
    """
    _logger = configuration.logger
    # NOTE: we use a custom field to extract base with requested_url_base
    uri_field = 'VERIFY_URL'
    fake_env = {uri_field: req_url}
    base_url = requested_url_base(fake_env, True, uri_field)
    local_url_anchors = (configuration.migserver_http_url,
                         configuration.migserver_https_url,
                         configuration.migserver_public_url,
                         configuration.migserver_public_alias_url,
                         configuration.migserver_https_mig_cert_url,
                         configuration.migserver_https_ext_cert_url,
                         configuration.migserver_https_mig_oid_url,
                         configuration.migserver_https_ext_oid_url,
                         configuration.migserver_https_mig_oidc_url,
                         configuration.migserver_https_ext_oidc_url,
                         configuration.migserver_https_sid_url)
    for site_url in local_url_anchors:
        if base_url == site_url or base_url.startswith('/') or \
                base_url.startswith('%s/' % site_url):
            return True
    _logger.error("local site request verification failed: %r" % req_url)
    return False


def is_unicode(val):
    """Return boolean indicating if val is a unicode string. We avoid
    `isinstance(val, unicode)`
    and the like since it breaks when combined with python-future and futurize.
    """
    return (type(u"") == type(val))


def force_utf8(val, highlight=''):
    """Internal helper to encode unicode strings to utf8 version. Actual
    changes are marked out with the highlight string if given.
    """
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, basestring):
        val = "%s" % val
    if not is_unicode(val):
        return val
    return "%s%s%s" % (highlight, val.encode("utf8"), highlight)


def force_utf8_rec(input_obj, highlight=''):
    """Recursive object conversion from unicode to utf8: useful to convert e.g.
    dictionaries with nested unicode strings to a pure utf8 version. Actual
    changes are marked out with the highlight string if given.
    """
    if isinstance(input_obj, dict):
        return {force_utf8_rec(i, highlight): force_utf8_rec(j, highlight) for (i, j) in
                input_obj.items()}
    elif isinstance(input_obj, list):
        return [force_utf8_rec(i, highlight) for i in input_obj]
    elif is_unicode(input_obj):
        return force_utf8(input_obj, highlight)
    else:
        return input_obj


def force_unicode(val, highlight=''):
    """Internal helper to decode unicode strings from utf8 version. Actual
    changes are marked out with the highlight string if given.
    """
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, basestring):
        val = "%s" % val
    if not is_unicode(val):
        return "%s%s%s" % (highlight, val.decode("utf8"), highlight)
    return val


def force_unicode_rec(input_obj, highlight=''):
    """Recursive object conversion from utf8 to unicode: useful to convert e.g.
    dictionaries with nested utf8 strings to a pure unicode version. Actual
    changes are marked out with the highlight string if given.
    """
    if isinstance(input_obj, dict):
        return {force_unicode_rec(i, highlight): force_unicode_rec(j, highlight) for (i, j) in
                input_obj.items()}
    elif isinstance(input_obj, list):
        return [force_unicode_rec(i, highlight) for i in input_obj]
    elif not is_unicode(input_obj):
        return force_unicode(input_obj, highlight)
    else:
        return input_obj


def _force_default_coding(input_obj, kind, highlight=''):
    """A helper to force input_obj to the default coding for given kind.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    if kind == STR_KIND and default_str_coding == "unicode" or \
            kind == FS_KIND and default_fs_coding == "unicode":
        return force_unicode(input_obj, highlight)
    elif kind == STR_KIND and default_str_coding == "utf8" or \
            kind == FS_KIND and default_fs_coding == "utf8":
        return force_utf8(input_obj, highlight)
    else:
        raise ValueError('Unsupported default coding kind: %s' % kind)


def force_default_str_coding(input_obj, highlight=''):
    """A helper to force input_obj to the default string coding.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    return _force_default_coding(input_obj, STR_KIND, highlight)


def force_default_fs_coding(input_obj, highlight=''):
    """A helper to force input_obj to the default filesystem coding.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    return _force_default_coding(input_obj, FS_KIND, highlight)


def force_native_str(input_obj, highlight=''):
    """A helper to force input_obj to the default string coding.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    return _force_default_coding(input_obj, STR_KIND, highlight)


def force_native_fs(input_obj, highlight=''):
    """A helper to force input_obj to the default filesystem coding.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    return _force_default_coding(input_obj, FS_KIND, highlight)


def _force_default_coding_rec(input_obj, kind, highlight=''):
    """A helper to force all strings in input_obj into the python-specific
    default string coding recursively.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    if kind == STR_KIND and default_str_coding == "unicode" or \
            kind == FS_KIND and default_fs_coding == "unicode":
        return force_unicode_rec(input_obj, highlight)
    elif kind == STR_KIND and default_str_coding == "utf8" or \
            kind == FS_KIND and default_fs_coding == "utf8":
        return force_utf8_rec(input_obj, highlight)
    else:
        raise ValueError('Unsupported default coding kind: %s' % kind)


def force_default_str_coding_rec(input_obj, highlight=''):
    """A helper to force input_obj to the default string coding recursively.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    return _force_default_coding_rec(input_obj, STR_KIND, highlight)


def force_default_fs_coding_rec(input_obj, highlight=''):
    """A helper to force input_obj to the default filesystem coding recursively.
    Use the active interpreter and the shared.defaults helpers to force the
    current default.
    """
    return _force_default_coding_rec(input_obj, FS_KIND, highlight)


def _is_default_coding(input_str, kind):
    """Checks if input_str is on the default coding form for given kind"""
    if is_unicode(input_str):
        if kind == STR_KIND and default_str_coding == "unicode" or \
                kind == FS_KIND and default_fs_coding == "unicode":
            return True
        else:
            return False
    else:
        if kind == STR_KIND and default_str_coding == "utf8" or \
                kind == FS_KIND and default_fs_coding == "utf8":
            return True
        else:
            return False


def is_default_str_coding(input_str):
    """Checks if input_str is on the default_str_coding form"""
    return _is_default_coding(input_str, STR_KIND)


def is_default_fs_coding(input_str):
    """Checks if input_str is on the default_fs_coding form"""
    return _is_default_coding(input_str, FS_KIND)


def get_xgi_bin(configuration, force_legacy=False):
    """Lookup the preferred Xgi-bin for server URLs. If WSGI is enabled in the
    configuration wsgi-bin is used. Otherwise the legacy cgi-bin is used.
    The optional force_legacy argument can be used to force legacy cgi-bin use
    e.g. for scripts that are not supported in WSGI.
    """

    if not force_legacy and configuration.site_enable_wsgi:
        return 'wsgi-bin'
    return 'cgi-bin'


def generate_https_urls(configuration, url_template, helper_dict):
    """Generate a string with one or more URLS for enabled https login
    methods. The url_template is filled with helper_dict, the best available
    auto_bin web provider method and in turn with the auto_base parameter set
    to the HTTPS URL of enabled login method in prioritized order.
    """
    local_helper = {}
    local_helper.update(helper_dict)
    local_helper['auto_bin'] = 'cgi-bin'
    if configuration.site_enable_wsgi:
        local_helper['auto_bin'] = 'wsgi-bin'
    mig_cert_url = configuration.migserver_https_mig_cert_url
    ext_cert_url = configuration.migserver_https_ext_cert_url
    mig_oid_url = configuration.migserver_https_mig_oid_url
    ext_oid_url = configuration.migserver_https_ext_oid_url
    mig_oidc_url = configuration.migserver_https_mig_oidc_url
    ext_oidc_url = configuration.migserver_https_ext_oidc_url
    locations = []
    for i in configuration.site_login_methods:
        if i == 'migcert' and mig_cert_url and not mig_cert_url in locations:
            locations.append(mig_cert_url)
        elif i == 'extcert' and ext_cert_url and not ext_cert_url in locations:
            locations.append(ext_cert_url)
        elif i == 'migoid' and mig_oid_url and not mig_oid_url in locations:
            locations.append(mig_oid_url)
        elif i == 'extoid' and ext_oid_url and not ext_oid_url in locations:
            locations.append(ext_oid_url)
        elif i == 'migoidc' and mig_oidc_url and not mig_oidc_url in locations:
            locations.append(mig_oidc_url)
        elif i == 'extoidc' and ext_oidc_url and not ext_oidc_url in locations:
            locations.append(ext_oidc_url)
    filled_list = []
    for https_base in locations:
        local_helper['auto_base'] = https_base
        filled_list.append(url_template % local_helper)
    url_str = '\nor\n'.join(filled_list)
    if locations[1:]:
        url_str += '''
(The URL depends on whether you log in with OpenID or a user certificate -
just use the one that looks most familiar or try them in turn)'''
    return url_str


def valid_dir_input(base, variable):
    """This function verifies that user supplied variable used as a directory
    in file manipulation doesn't try to illegally access directories by
    using e.g. '..'. The base argument is the directory that the user
    should be bound to, and the variable is the variable to be checked.
    The verification amounts to verifying that base/variable doesn't
    expand to a path outside base or among the invisible paths.
    """

    # Please note that base_dir must end in slash to avoid access to other
    # dirs when variable is a prefix of another dir in base

    path = os.path.abspath(base) + os.sep + variable
    if os.path.abspath(path) != path or invisible_path(path):

        # out of bounds

        return False
    return True


def user_base_dir(configuration, client_id, trailing_slash=True):
    """This function returns the absolute path for the home directory of client_id.
    By default a trailing slash is appended to the path before it
    is returned but it can be disabled with the boolean trailing_slash argument.
    If no client_id is provided, False is returned instead.
    """
    if not client_id:
        return False
    client_dir = client_id_dir(client_id)
    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir))
    if trailing_slash:
        base_dir += os.sep
    return base_dir


def allow_script(configuration, script_name, client_id):
    """Helper to detect if script_name is allowed to run or not based on site
    configuration. I.e. GDP-mode disables a number of functionalities.
    """
    _logger = configuration.logger
    # _logger.debug("in allow_script for %s from %s" % (script_name, client_id))
    if configuration.site_enable_gdp:
        # _logger.debug("in allow_script gdp for %s" % script_name)
        reject_append = " functionality disabled by site configuration!"
        if not client_id:
            if script_name in valid_gdp_anon_scripts:
                allow = True
                msg = ""
            else:
                allow = False
                msg = "anonoymous access to" + reject_append
        else:
            if script_name in valid_gdp_auth_scripts + valid_gdp_anon_scripts:
                allow = True
                msg = ""
            else:
                allow = False
                msg = "all access to" + reject_append
    else:
        allow, msg = True, ''
    # _logger.debug("allow_script returns %s for %s" % (allow, script_name))
    return (allow, msg)


def string_snippet(full_string, max_size=32):
    """Returns a shortened version of full_string with the middle part cut out.
    Removes the central half or more to make sure the resulting string is at
    most max_size characters long. Useful to e.g. prevent disclosing actual
    contents of password hashes in logs while maintaining debugging hints.
    NOTE: an even max_size value of at least 8 is expected for simpler math.
    """
    snip_mark = ' .. '
    if max_size % 2 != 0 or max_size < 2 * len(snip_mark):
        raise ValueError("max_size must be an even number >= %d (got %s)" %
                         (2 * len(snip_mark), max_size))
    if len(full_string) <= len(snip_mark):
        return snip_mark
    elif len(full_string) / 2 + len(snip_mark) <= max_size:
        chunk_size = len(full_string) / 4
    else:
        chunk_size = (max_size - len(snip_mark)) / 2
    return full_string[:chunk_size] + snip_mark + full_string[-chunk_size:]


def brief_list(full_list, max_entries=10):
    """Takes full_list and returns a potentially shortened representation with
    at most max_entries elements where any excess elements are pruned from the
    center. Similar to numpy string output of big arrays.
    """
    if not full_list[max_entries:]:
        return full_list
    half_entries = max_entries // 2
    # NOTE: full_list may be a range which needs special care in py3
    return list(full_list[:half_entries]) + [' ... shortened ... '] + \
        list(full_list[-half_entries:])


def auth_type_description(configuration, auth_type=keyword_all):
    """Shared helper for auth_type description lookup. Returns the description
    for auth_type if one is provided and otherwise the dictionary of known
    auth_types and their descriptions.
    """
    auth_map = {'migoid': '%s %s' %
                (configuration.user_mig_oid_title, AUTH_OPENID_V2),
                'migoidc': '%s %s' %
                (configuration.user_mig_oid_title, AUTH_OPENID_CONNECT),
                'migcert': '%s %s' %
                (configuration.user_mig_cert_title, AUTH_CERTIFICATE),
                'extoid': '%s %s' %
                (configuration.user_ext_oid_title, AUTH_OPENID_V2),
                'extoidc': '%s %s' %
                (configuration.user_ext_oid_title, AUTH_OPENID_CONNECT),
                'extcert': '%s %s' %
                (configuration.user_ext_cert_title, AUTH_CERTIFICATE),
                }
    if auth_type == keyword_all:
        return auth_map
    else:
        return auth_map.get(auth_type, 'UNKNOWN')


if __name__ == '__main__':
    orig_id = '/C=DK/ST=NA/L=NA/O=Ajax Inc/OU=NA/CN=John Doe/emailAddress=john.doe@ajaxinc.org'
    client_dir = client_id_dir(orig_id)
    client_id = client_dir_id(client_dir)
    test_paths = ['simple.txt', 'somedir/somefile.txt']
    sample_file = _user_invisible_files[0]
    sample_dir = _user_invisible_dirs[0]
    illegal = ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in
               [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
                ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
                ('', '/sub'), ('', '/sub/sample.txt'),
                ('somedir/', '/sample.txt'), ('/somedir/', '/sample.txt'),
                ('/somedir/sub/', '/sample.txt')]] + \
        ["%s%s" % (prefix, sample_file) for prefix, _ in
         [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
          ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
          ]]
    legal = ["%s%s%s" % (prefix, sample_file, suffix) for (prefix, suffix) in
             [('prefix', ''), ('somedir/prefix', ''), ('', 'suffix'),
              ('', 'suffix/somedir'), ('prefix', 'suffix')]] +\
        ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in
         [('prefix', ''), ('somedir/prefix', ''), ('', 'suffix'),
          ('', 'suffix/somedir'), ('prefix', 'suffix')]]
    legal += ['sample.txt', 'somedir/sample.txt', '/somedir/sample.txt']
    print("orig id %s, dir %s, id %s (match %s)" %
          (orig_id, client_dir, client_id, orig_id == client_id))
    print("invisible tests")
    print("check that these are invisible:")
    for path in illegal:
        print("  %s: %s" % (path, invisible_path(path)))
    print("make sure these are not invisible:")
    for path in legal:
        print("  %s: %s" % (path, not invisible_path(path)))

    from mig.shared.conf import get_configuration_object
    configuration = get_configuration_object()
    print("check script restrictions:")
    for script_name in ['reqoid.py', 'ls.py', 'sharelink.py', 'put']:
        (allow, msg) = allow_script(configuration, script_name, '')
        print("check %s without client id: %s %s" % (script_name, allow, msg))
        (allow, msg) = allow_script(configuration, script_name, client_id)
        print("check %s with client id '%s': %s %s" % (script_name, client_id,
                                                       allow, msg))
    print("brief format of short list: %s" % brief_list(range(5)))
    print("brief format of long list: %s" % brief_list(range(30)))
    print("brief format of huge list: %s" % brief_list(range(200)))

    for str_len in [1, 4, 8, 12, 16, 24, 32, 60, 61, 62, 63, 64, 65, 66, 67, 68, 72, 128]:
        orig = ''.join(['%d' % (i % 10) for i in range(str_len)])
        snippet = string_snippet(orig)
        print("string snippet of %r (%d) is %r (%d)" % (orig, len(orig),
                                                        snippet, len(snippet)))

    user_dict = distinguished_name_to_user(client_id)
    user_dict.update({'password': 'NotSoSecretDummy',
                      'password_encrypted': '0123456789abcdef',
                      'password_hash': '0123456789abcdef',
                      'password_digest': '0123456789abcdef'})
    user_dict = canonical_user(configuration, user_dict, user_dict.keys())
    print("Apply mask creds on bogus user dict:\n%s\nresults in:\n%s" %
          (user_dict, mask_creds(user_dict)))

    check_uris = [
        'https://localhost',
        'https://localhost/cgi-sid/BACKEND.py',
        'https://localhost/cgi-sid/BACKEND.py/UNSAFECONTENT?VALIDQUERY',
        'https://localhost/cgi-sid/BACKEND.py/><img src=dummy onerror="alert(\'RXSS\')%22%3E?show=ALL',
    ]
    for script_uri in check_uris:
        os.environ['SCRIPT_URI'] = script_uri
        os.environ['SCRIPT_NAME'] = script_uri.replace('https://localhost', '')
        if script_uri.find('.py') != -1:
            os.environ['SCRIPT_NAME'] = script_uri.split('.py', 1)[0] + '.py'
        print("Found backend for %r : %s" % (script_uri, requested_backend()))
        print("Found page for %r : %s" % (script_uri, requested_page()))
        print("Found page name for %r : %s" %
              (script_uri, requested_page(name_only=True)))
        print("Found url base for %r : %s" %
              (script_uri, requested_url_base()))
        print("Found unsafe page for %r : %s" %
              (script_uri, requested_page(include_unsafe=True)))
