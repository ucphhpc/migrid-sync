# -*- coding: utf-8 -*-
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

# From https://github.com/mitsuhiko/python-pbkdf2
from pbkdf2 import pbkdf2_bin


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

def check_hash(password, hash_, hash_cache=None):
    """Check a password against an existing hash. The optional hash_cache
    dictionary argument can be used to cache recent lookups to save time in
    e.g. webdav where each operation triggers hash check.
    """
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    pw_hash = hashlib.md5(password).hexdigest()
    if isinstance(hash_cache, dict) and \
           hash_cache.get(pw_hash, None) == hash_:
        #print "found cached hash: %s" % hash_cache.get(pw_hash, None)
        return True
    algorithm, hash_function, cost_factor, salt, hash_a = hash_.split('$')
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
        hash_cache[pw_hash] = hash_
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

def check_digest(realm, username, password, digest, salt, digest_cache=None):
    """Check credentials against an existing digest. The optional digest_cache
    dictionary argument can be used to cache recent lookups to save time in
    e.g. webdav where each operation triggers digest check.
    """
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
    match = (make_digest(realm, username, password, salt) == digest) 
    if isinstance(digest_cache, dict) and match:
        digest_cache[creds_hash] = digest
        # print "cached digest: %s" % digest_cache.get(creds_hash, None)
    return match 
