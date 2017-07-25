#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# pwhash - helpers for passwords and hashing
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""

    Securely hash and check passwords using PBKDF2.

    Use random salts to protect againt rainbow tables, many iterations against
    brute-force, and constant-time comparaison againt timing attacks.

    Keep parameters to the algorithm together with the hash so that we can
    change the parameters and keep older hashes working.

    See more details at http://exyr.org/2011/hashing-passwords/

    Author: Simon Sapin
    License: BSD

"""

import hashlib
from os import urandom
from base64 import b64encode, b64decode, b16encode, b16decode
from itertools import izip
from string import lowercase, uppercase, digits
# From https://github.com/mitsuhiko/python-pbkdf2
from pbkdf2 import pbkdf2_bin

from shared.defaults import POLICY_NONE, POLICY_WEAK, POLICY_MEDIUM, \
     POLICY_HIGH

# Parameters to PBKDF2. Only affect new passwords.
SALT_LENGTH = 12
KEY_LENGTH = 24
HASH_FUNCTION = 'sha256'  # Must be in hashlib.
# Linear to the hashing time. Adjust to be high but take a reasonable
# amount of time on your server. Measure with:
# python -m timeit -s 'import passwords as p' 'p.make_hash("something")'
COST_FACTOR = 10000


def make_hash(password):
    """Generate a random salt and return a new hash for the password."""
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    salt = b64encode(urandom(SALT_LENGTH))
    # Python 2.6 fails to parse implicit positional args (-Jonas)
    #return 'PBKDF2${}${}${}${}'.format(
    return 'PBKDF2${0}${1}${2}${3}'.format(
        HASH_FUNCTION,
        COST_FACTOR,
        salt,
        b64encode(pbkdf2_bin(password, salt, COST_FACTOR, KEY_LENGTH,
                             getattr(hashlib, HASH_FUNCTION))))

# TODO: switch to strict_policy by default
def check_hash(configuration, service, username, password, hashed,
               hash_cache=None, strict_policy=False):
    """Check a password against an existing hash. First make sure the provided
    password satisfies the local password policy. The optional hash_cache
    dictionary argument can be used to cache recent lookups to save time in
    e.g. webdav where each operation triggers hash check.
    """
    _logger = configuration.logger
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    pw_hash = hashlib.md5(password).hexdigest()
    if isinstance(hash_cache, dict) and \
           hash_cache.get(pw_hash, None) == hashed:
        #print "found cached hash: %s" % hash_cache.get(pw_hash, None)
        return True
    # We check policy AFTER cache lookup since it is already verified for those
    try:
        assure_password_strength(configuration, password)
    except Exception, exc:
        _logger.warning("%s password for %s does not fit local policy: %s" \
                        % (service, username, exc))
        if strict_policy:
            return False
    algorithm, hash_function, cost_factor, salt, hash_a = hashed.split('$')
    assert algorithm == 'PBKDF2'
    hash_a = b64decode(hash_a)
    hash_b = pbkdf2_bin(password, salt, int(cost_factor), len(hash_a),
                        getattr(hashlib, hash_function))
    assert len(hash_a) == len(hash_b)  # we requested this from pbkdf2_bin()
    # Same as "return hash_a == hash_b" but takes a constant time.
    # See http://carlos.bueno.org/2011/10/timing.html
    diff = 0
    for char_a, char_b in izip(hash_a, hash_b):
        diff |= ord(char_a) ^ ord(char_b)
    match = (diff == 0)
    if isinstance(hash_cache, dict) and match:
        hash_cache[pw_hash] = hashed
        #print "cached hash: %s" % hash_cache.get(pw_hash, None)
    return match

def scramble_digest(salt, digest):
    """Scramble digest for saving"""
    b16_digest = b16encode(digest)
    xor_int = int(salt, 16) ^ int(b16_digest, 16)
    # Python 2.6 fails to parse implicit positional args (-Jonas)
    #return '{:X}'.format(xor_int)
    return '{0:X}'.format(xor_int)

def unscramble_digest(salt, digest):
    """Unscramble loaded digest"""
    xor_int = int(salt, 16) ^ int(digest, 16)
    # Python 2.6 fails to parse implicit positional args (-Jonas)
    #b16_digest = '{:X}'.format(xor_int)
    b16_digest = '{0:X}'.format(xor_int)
    return b16decode(b16_digest)

def make_digest(realm, username, password, salt):
    """Generate a digest for the credentials"""
    merged_creds = ':'.join([realm, username, password])
    # TODO: can we switch to proper md5 hexdigest without breaking webdavs?
    digest = 'DIGEST$custom$CONFSALT$%s' % scramble_digest(salt, merged_creds)
    return digest

# TODO: switch to strict_policy by default
def check_digest(configuration, service, realm, username, password, digest,
                 salt, digest_cache=None, strict_policy=False):
    """Check credentials against an existing digest. First make sure the
    provided password satisfies the local password policy. The optional
    digest_cache dictionary argument can be used to cache recent lookups to
    save time in e.g. webdav where each operation triggers digest check.
    """
    _logger = configuration.logger
    if isinstance(realm, unicode):
        realm = realm.encode('utf-8')
    if isinstance(username, unicode):
        username = username.encode('utf-8')
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    merged_creds = ':'.join([realm, username, password])
    creds_hash = hashlib.md5(merged_creds).hexdigest()
    if isinstance(digest_cache, dict) and \
           digest_cache.get(creds_hash, None) == digest:
        # print "found cached digest: %s" % digest_cache.get(creds_hash, None)
        return True
    # We check policy AFTER cache lookup since it is already verified for those
    try:
        assure_password_strength(configuration, password)
    except Exception, exc:
        _logger.warning("%s password for %s does not fit local policy: %s" \
                        % (service, username, exc))
        if strict_policy:
            return False
    match = (make_digest(realm, username, password, salt) == digest)
    if isinstance(digest_cache, dict) and match:
        digest_cache[creds_hash] = digest
        # print "cached digest: %s" % digest_cache.get(creds_hash, None)
    return match 

def scramble_password(salt, password):
    """Scramble password for saving"""
    b64_password = b64encode(password)
    if not salt:
        return b64_password
    xor_int = int(salt, 64) ^ int(b64_password, 64)
    # Python 2.6 fails to parse implicit positional args (-Jonas)
    #return '{:X}'.format(xor_int)
    return '{0:X}'.format(xor_int)

def unscramble_password(salt, password):
    """Unscramble loaded password"""
    if salt:
        xor_int = int(salt, 64) ^ int(password, 64)
        # Python 2.6 fails to parse implicit positional args (-Jonas)
        #b64_digest = '{:X}'.format(xor_int)
        b64_password = '{0:X}'.format(xor_int)
    else:
        b64_password = password
    return b64decode(b64_password)

def make_scramble(password, salt):
    """Generate a scrambled password"""
    return scramble_password(salt, password)

def check_scramble(configuration, service, username, password, scrambled,
                   salt=None, scramble_cache=None, strict_policy=True):
    """Make sure provided password satisfies local password policy and check
    match against existing scrambled password. The optional scramble_cache
    dictionary argument can be used to cache recent lookups to save time in
    e.g. openid where each operation triggers check.
    
    NOTE: we force strict password policy here since we expect weak legacy
    passwords in the user DB and they would easily give full account access.
    """
    _logger = configuration.logger
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    if isinstance(scramble_cache, dict) and \
           scramble_cache.get(password, None) == scrambled:
        # print "found cached scramble: %s" % scramble_cache.get(password, None)
        return True
    # We check policy AFTER cache lookup since it is already verified for those
    try:
        assure_password_strength(configuration, password)
    except Exception, exc:
        _logger.warning('%s password for %s does not satisfy local policy: %s' \
                        % (service, username, exc))
        if strict_policy:
            return False
    match = (make_scramble(password, salt) == scrambled)
    if isinstance(scramble_cache, dict) and match:
        scramble_cache[password] = scrambled
        # print "cached digest: %s" % scramble_cache.get(password, None)
    return match

def make_csrf_token(configuration, method, operation, client_id, limit=None):
    """Generate a Cross-Site Request Forgery (CSRF) token to help verify the
    authenticity of user requests. The optional limit argument can be used to
    e.g. put a timestamp into the mix, so that the token automatically expires. 
    """
    salt = configuration.site_digest_salt
    merged = "%s:%s:%s:%s" % (method, operation, client_id, limit)
    configuration.logger.debug("CSRF for %s" % merged)
    xor_id = "%s" % (int(salt, 16) ^ int(b16encode(merged), 16))
    token = hashlib.sha256(xor_id).hexdigest()
    return token

def assure_password_strength(configuration, password):
    """Make sure password fits site password policy in terms of length and
    number of different character classes.
    We split into four classes for now, lowercase, uppercase, digits and other.
    """
    logger = configuration.logger
    site_policy = configuration.site_password_policy
    policy_fail_msg = 'password does not fit site password policy'
    if site_policy == POLICY_NONE:
        logger.debug('site password policy allows any password')
        min_len, min_classes = 0, 0
    elif site_policy == POLICY_WEAK:
        min_len, min_classes = 6, 2
    elif site_policy == POLICY_MEDIUM:
        min_len, min_classes = 8, 3
    elif site_policy == POLICY_HIGH:
        min_len, min_classes = 10, 4
    else:
        raise Exception('invalid site password policy')
    if len(password) < min_len:
        err_msg = '%s: too short, at least %d chars required' % \
                  (policy_fail_msg, min_len)
        logger.warning(err_msg)
        raise ValueError(err_msg)
    char_class_map = {'lower': lowercase, 'upper': uppercase, 'digits': digits}
    base_chars = ''.join(char_class_map.values())
    pw_classes = []
    for i in password:
        if i not in base_chars and 'other' not in pw_classes:
            pw_classes.append('other')
            continue
        for (char_class, values) in char_class_map.items():
            if i in values and not char_class in pw_classes:
                pw_classes.append(char_class)
                break
    if len(pw_classes) < min_classes:
        err_msg = '%s: too simple, at least %d character classes required' % \
                  (policy_fail_msg, min_classes)
        logger.warning(err_msg)
        raise ValueError(err_msg)
    logger.debug('password compliant with site password policy (%s)' % \
                 site_policy)
    return True
