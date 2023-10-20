#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
#
# pwcrypto - helpers for password and crypto including for encryption and hashing
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Helpers for various password policy, crypt and hashing activities"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import zip, range
from base64 import b64encode, b64decode, b16encode, b16decode, \
    urlsafe_b64encode, urlsafe_b64decode
from os import urandom
from random import SystemRandom
from string import ascii_lowercase, ascii_uppercase, digits
import datetime
import hashlib
import time

from mig.shared.base import force_utf8, mask_creds, string_snippet
from mig.shared.defaults import keyword_auto, RESET_TOKEN_TTL


try:
    import cracklib
except ImportError:
    # Optional cracklib not available - fail gracefully and check before use
    cracklib = None
try:
    import cryptography
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    # Optional cryptography not available - fail gracefully and check before use
    cryptography = None

from mig.shared.defaults import POLICY_NONE, POLICY_WEAK, POLICY_MEDIUM, \
    POLICY_HIGH, POLICY_MODERN, POLICY_CUSTOM, PASSWORD_POLICIES

# Parameters to PBKDF2. Only affect new passwords.
SALT_LENGTH = 12
KEY_LENGTH = 24
HASH_FUNCTION = 'sha256'  # Must be in hashlib.
# Linear to the hashing time. Adjust to be high but take a reasonable
# amount of time on your server. Measure with:
# python -m timeit -s 'import passwords as p' 'p.make_hash("something")'
COST_FACTOR = 10000

# AESGCM helpers to build the Additional Authenticated Data (AAD) values.
# Please note that the values increase on a daily basis by default so the
# encryption values will always change at least with that rate even for the
# same input and Initialization Vector (IV). Please refer to the encrypt and
# decrypt functions for further details.
AAD_PREFIX = 'migrid authenticated'
AAD_DEFAULT_STAMP = '%Y%m%d'

# NOTE hook up available hashing algorithms once and for all
valid_hash_algos = {'md5': hashlib.md5}
for algo in hashlib.algorithms_guaranteed:
    valid_hash_algos[algo] = getattr(hashlib, algo)


def best_crypt_salt(configuration):
    """Look up configured salts in turn and pick first suitable"""
    _logger = configuration.logger
    if configuration.site_crypto_salt:
        # _logger.debug('making crypto key from crypto salt and entropy')
        salt_data = configuration.site_crypto_salt
    elif configuration.site_password_salt:
        # _logger.debug('making crypto key from pw salt and entropy')
        salt_data = configuration.site_password_salt
    elif configuration.site_digest_salt:
        # _logger.debug('making crypto key from digest salt and entropy')
        salt_data = configuration.site_digest_salt
    else:
        raise Exception('cannot find a suitbale crypt salt in conf')
    return salt_data


def make_hash(password):
    """Generate a random salt and return a new hash for the password."""
    salt = b64encode(urandom(SALT_LENGTH))
    derived = b64encode(hashlib.pbkdf2_hmac(HASH_FUNCTION, 
                                            force_utf8(password), salt, 
                                            COST_FACTOR, KEY_LENGTH))
    return 'PBKDF2${}${}${}${}'.format(HASH_FUNCTION, COST_FACTOR,
                                       salt, derived)


def check_hash(configuration, service, username, password, hashed,
               hash_cache=None, strict_policy=True, allow_legacy=False):
    """Check a password against an existing hash. First make sure the provided
    password satisfies the local password policy. The optional hash_cache
    dictionary argument can be used to cache recent lookups to save time in
    e.g. webdav where each operation triggers hash check.
    The optional boolean strict_policy argument decides whether or not the site
    password policy is enforced. It is used to disable checks for e.g.
    sharelinks where the policy is not guaranteed to apply.
    The optional boolean allow_legacy argument extends the strict_policy check
    so that passwords matching any configured password legacy policy are also
    accepted. Use only during active log in checks.
    """
    _logger = configuration.logger
    # NOTE: hashlib works with bytes
    hash_bytes = force_utf8(hashed)
    pw_hash = make_simple_hash(password)
    if isinstance(hash_cache, dict) and \
            hash_cache.get(pw_hash, None) == hash_bytes:

        # _logger.debug("got cached hash: %s" % [hash_cache.get(pw_hash, None)])
        return True
    # We check policy AFTER cache lookup since it is already verified for those
    if strict_policy:
        try:
            assure_password_strength(configuration, password, allow_legacy)
        except Exception as exc:
            _logger.warning("%s password for %s does not fit local policy: %s"
                            % (service, username, exc))
            return False
    else:
        _logger.debug("password policy check disabled for %s login as %s" %
                      (service, username))
    algorithm, hash_function, cost_factor, salt, hash_a = hashed.split('$')
    assert algorithm == 'PBKDF2'
    hash_a = b64decode(hash_a)
    # NOTE: pbkdf2_hmac requires bytes for password and salt
    pw_bytes = force_utf8(password)
    hash_b = hashlib.pbkdf2_hmac(hash_function, pw_bytes, force_utf8(salt),
                                 int(cost_factor), len(hash_a))
    assert len(hash_a) == len(hash_b)  # we requested this from pbkdf2_hmac()
    # Same as "return hash_a == hash_b" but takes a constant time.
    # See http://carlos.bueno.org/2011/10/timing.html
    diff = 0
    for char_a, char_b in zip(hash_a, hash_b):
        diff |= ord(char_a) ^ ord(char_b)
    match = (diff == 0)
    if isinstance(hash_cache, dict) and match:
        hash_cache[pw_hash] = hash_bytes
        # print("cached hash: %s" % hash_cache.get(pw_hash, None))
    return match


def scramble_digest(salt, digest):
    """Scramble digest for saving"""
    b16_digest = b16encode(digest)
    xor_int = int(salt, 16) ^ int(b16_digest, 16)
    # Python 2.6 fails to parse implicit positional args (-Jonas)
    # return '{:X}'.format(xor_int)
    return '{0:X}'.format(xor_int)


def unscramble_digest(salt, digest):
    """Unscramble loaded digest"""
    xor_int = int(salt, 16) ^ int(digest, 16)
    # Python 2.6 fails to parse implicit positional args (-Jonas)
    # b16_digest = '{:X}'.format(xor_int)
    b16_digest = '{0:X}'.format(xor_int)
    return b16decode(b16_digest)


def make_digest(realm, username, password, salt):
    """Generate a digest for the credentials"""
    merged_creds = ':'.join([realm, username, password])
    # TODO: can we switch to proper md5 hexdigest without breaking webdavs?
    digest = 'DIGEST$custom$CONFSALT$%s' % scramble_digest(salt, merged_creds)
    return digest


def check_digest(configuration, service, realm, username, password, digest,
                 salt, digest_cache=None, strict_policy=True,
                 allow_legacy=False):
    """Check credentials against an existing digest. First make sure the
    provided password satisfies the local password policy. The optional
    digest_cache dictionary argument can be used to cache recent lookups to
    save time in e.g. webdav where each operation triggers digest check.
    The optional boolean strict_policy argument changes warnings about password
    policy incompliance to unconditional rejects.
    The optional boolean allow_legacy argument extends the strict_policy check
    so that passwords matching any configured password legacy policy are also
    accepted. Use only during active log in checks.
    """
    _logger = configuration.logger
    merged_creds = ':'.join([realm, username, password])
    creds_hash = make_simple_hash(merged_creds)
    if isinstance(digest_cache, dict) and \
            digest_cache.get(creds_hash, None) == digest:
        # print("got cached digest: %s" % digest_cache.get(creds_hash, None))
        return True
    # We check policy AFTER cache lookup since it is already verified for those
    try:
        assure_password_strength(configuration, password, allow_legacy)
    except Exception as exc:
        _logger.warning("%s password for %s does not fit local policy: %s"
                        % (service, username, exc))
        if strict_policy:
            return False
    computed = make_digest(realm, username, password, salt)
    match = (computed == digest)
    if isinstance(digest_cache, dict) and match:
        digest_cache[creds_hash] = digest
        # print("cached digest: %s" % digest_cache.get(creds_hash, None))
    return match


def scramble_password(salt, password):
    """Scramble password for saving with fallback to base64 encoding if no salt
    is provided.
    """
    if not salt or not password:
        return b64encode(password)
    xor_int = int(salt, 16) ^ int(b16encode(password), 16)
    return '{0:X}'.format(xor_int)


def unscramble_password(salt, password):
    """Unscramble loaded password with fallback to base64 decoding if no salt
    is provided.
    """
    if not salt:
        unscrambled = b64decode(password)
        return unscrambled
    xor_int = int(salt, 16) ^ int(password, 16)
    b16_password = '{0:X}'.format(xor_int)
    return b16decode(b16_password)


def make_scramble(password, salt):
    """Generate a scrambled password"""
    return scramble_password(salt, password)


def check_scramble(configuration, service, username, password, scrambled,
                   salt=None, scramble_cache=None, strict_policy=True,
                   allow_legacy=False):
    """Make sure provided password satisfies local password policy and check
    match against existing scrambled password. The optional scramble_cache
    dictionary argument can be used to cache recent lookups to save time in
    e.g. openid where each operation triggers check.

    NOTE: we force strict password policy here since we may find weak legacy
    passwords in the user DB and they would easily give full account access.
    The optional boolean allow_legacy argument extends the strict_policy check
    so that passwords matching any configured password legacy policy are also
    accepted. Use only during active log in checks.
    """
    _logger = configuration.logger
    if isinstance(scramble_cache, dict) and \
            scramble_cache.get(password, None) == scrambled:
        # print("got cached scramble: %s" % scramble_cache.get(password, None))
        return True
    # We check policy AFTER cache lookup since it is already verified for those
    try:
        assure_password_strength(configuration, password, allow_legacy)
    except Exception as exc:
        _logger.warning('%s password for %s does not satisfy local policy: %s'
                        % (service, username, exc))
        if strict_policy:
            return False
    computed = make_scramble(password, salt)
    match = (computed == scrambled)
    if isinstance(scramble_cache, dict) and match:
        scramble_cache[password] = scrambled
        # print("cached digest: %s" % scramble_cache.get(password, None))
    return match


def _prepare_encryption_key(configuration, secret=keyword_auto,
                            entropy=keyword_auto, key_bytes=32,
                            urlsafe=True):
    """Helper to extract and prepare a site-specific secret used for all
    encryption and decryption operations.
    """
    _logger = configuration.logger
    if not secret:
        _logger.error('encrypt/decrypt requested without a secret')
        raise Exception('cannot encrypt/decrypt without a secret')
    if secret == keyword_auto:
        # NOTE: generate a static secret key based on configuration.
        if entropy == keyword_auto:
            # Use previously generated 'entropy' each time from a call to
            # Fernet.generate_key() or AESGCM.generate_key()
            entropy = 'HyrqUFwxagFNcHANnDzVO-kMoU0ebo03pNaKHXce6xw='
        # yet salt it with hash of a site-specific and non-public salt
        # to avoid disclosing salt or final key.
        salt_data = best_crypt_salt(configuration)
        salt_hash = make_safe_hash(salt_data)
        key_data = scramble_password(salt_hash, entropy)
    else:
        # _logger.debug('making crypto key from provided secret')
        key_data = secret
    if urlsafe:
        key = urlsafe_b64encode(key_data[:key_bytes])
    else:
        key = key_data[:key_bytes]
    return key


def prepare_fernet_key(configuration, secret=keyword_auto):
    """Helper to extract and prepare a site-specific secret used for all
    Fernet encryption and decryption operations.
    """
    # NOTE: Fernet key must be 32 url-safe base64-encoded bytes
    return _prepare_encryption_key(configuration, secret, key_bytes=32)


def fernet_encrypt_password(configuration, password, secret=keyword_auto):
    """Encrypt password with strong Fernet algorithm for saving passwords and
    the like. Encryption implicitly relies on a random initialization vector
    for added security and the output for the same input therefore changes with
    every invocation. Please have a look at aes_encrypt_password with explicit
    init vectors if you need a strong but less secure static output for every
    invocation.
    """
    _logger = configuration.logger
    if cryptography:
        key = prepare_fernet_key(configuration, secret)
        password = force_utf8(password)
        fernet_helper = Fernet(key)
        encrypted = fernet_helper.encrypt(password)
    else:
        _logger.error('encrypt requested without cryptography installed')
        raise Exception('cryptography requested in conf but not available')
    return encrypted


def fernet_decrypt_password(configuration, encrypted, secret=keyword_auto):
    """Decrypt Fernet encrypted password"""
    _logger = configuration.logger
    if cryptography:
        key = prepare_fernet_key(configuration, secret)
        fernet_helper = Fernet(key)
        password = fernet_helper.decrypt(encrypted)
    else:
        _logger.error('decrypt requested without cryptography installed')
        raise Exception('cryptography requested in conf but not available')
    return password


def __aesgcm_pack_tuple(init_vector, encrypted, auth_data, base64_enc=True,
                        field_sep='.'):
    """A simple helper to pack the three-tuple of values from an aesgcm
    encryption.
    The packed string is simply values concatenated with field_sep as a
    separator. E.g. iv.crypt.aad with the default field_sep.
    By default the packed values are urlsafe base64 encoded, however, to avoid
    packing/unpacking interference with said separator.
    """
    parts = [init_vector, encrypted, auth_data]
    if base64_enc:
        parts = [urlsafe_b64encode(i) for i in parts]
    return field_sep.join(parts)


def __aesgcm_unpack_tuple(packed, base64_enc=True, field_sep='.'):
    """A simple helper to unpack a previously packed three-tuple of values from
    an aesgcm encryption.
    The packed string is simply values concatenated with field_sep as a
    separator. E.g. iv.crypt.aad with the default field_sep.
    By default the packed values are urlsafe-base64 encoded, however, to avoid
    packing/unpacking interference with said separator.
    """
    parts = packed.split(field_sep)
    if len(parts) != 3:
        raise ValueError("malformed packed values - expected 3 parts got %d" %
                         len(parts))
    if base64_enc:
        parts = [urlsafe_b64decode(i) for i in parts]
    return tuple(parts)


def _aesgcm_aad_helper(prefix, date_format=AAD_DEFAULT_STAMP, size=32):
    """Use a simple date as counter to keep AES authentication static for a while.
    The given date_format fields decide for how long by e.g. adding or removing
    the highest resolution fields. By default the output for a single input
    value remains constant for the rest of the day. One can adjust it to remain
    constant for an entire month by using '%Y%m' or for every single hour by
    using '%Y%m%d%H'.
    """
    crypt_counter = datetime.datetime.now().strftime(date_format)
    val = b' '*size + b'%s' % prefix
    val += b'%s' % crypt_counter
    return val[-size:]


def prepare_aesgcm_key(configuration, secret=keyword_auto):
    """Helper to extract and prepare a site-specific secret used for all
    AESGCM encryption and decryption operations.
    """
    # NOTE: AESGCM key must be 32 raw bytes
    return _prepare_encryption_key(configuration, secret, key_bytes=32,
                                   urlsafe=False)


def prepare_aesgcm_iv(configuration, iv_entropy=keyword_auto):
    """Helper to format a suitable Init Vector (IV) used for AESGCM encryption
    and decryption operations. If one provides a custom iv_entropy string the
    output will remain constant. Reusing the same IV for different messages
    breaks security so ONLY do something like that if repeatedly encrypting the
    same message and then e.g. with a strong hash of the value to encrypt.
    """
    # recommended IV of at least 96 bits (12 bytes) - use 128 (16 bytes)
    iv_bytes = 16
    if iv_entropy == keyword_auto:
        return urandom(iv_bytes)
    else:
        return iv_entropy[-iv_bytes:]


def prepare_aesgcm_aad(configuration, aad_prefix, aad_stamp=AAD_DEFAULT_STAMP):
    """Helper to make a suitable string of Additional Authenticated Data (AAD)
    used for authentication during AESGCM encryption and decryption operations.
    One can provide a custom aad_stamp string to have it evolve with time. The
    usual datetime string expansion variables are supported and the default
    uses the current YYYYMMDD date string.
    """
    aad_bytes = 32
    aad = _aesgcm_aad_helper(aad_prefix, aad_stamp, aad_bytes)
    return aad[-aad_bytes:]


def aesgcm_encrypt_password(configuration, password, secret=keyword_auto,
                            init_vector=keyword_auto,
                            aad_stamp=AAD_DEFAULT_STAMP,
                            base64_enc=True):
    """Encrypt password with strong AESGCM algorithm for saving passwords and
    the like. Encryption relies on a unique Initialization Vector (IV) for
    added security and the output for the same input changes with each such
    init_vector value. By default one is generated randomly each time and saved
    as part of the encrypted output. This will obviously make even repeated
    encryption calls for the same value differ. In case you need a strong but
    less secure STATIC output for every such repeated invocation, you can
    pick a fixed IV for each unique input. E.g. some safe hash of the input or
    similar. Just beware of the security implications if you do so.
    Similarly the aad_stamp defaults to be somewhat date dependent so aad will
    slowly but gradually change. You can tweak it to reduce or remove the flux
    but again please beware of the security implications if you do so.
    The output is the encryption three-tuple on packed string format, namely,
    the actual initialization vector used, the crypt string and the additional
    authentication data used. The latter two are NOT secret and will be needed
    for decrypting and verifying integrity.
    """
    _logger = configuration.logger
    # Based on complete example of securely encrypting with AES GCM from
    # https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption
    if cryptography:
        init_vector = prepare_aesgcm_iv(configuration, init_vector)
        auth_data = prepare_aesgcm_aad(configuration, AAD_PREFIX, aad_stamp)
        password = force_utf8(password)
        key = prepare_aesgcm_key(configuration, secret)
        aesgcm_helper = AESGCM(key)
        crypt = aesgcm_helper.encrypt(init_vector, password, auth_data)
        encrypted = __aesgcm_pack_tuple(init_vector, crypt, auth_data,
                                        base64_enc)
    else:
        _logger.error('encrypt requested without cryptography installed')
        raise Exception('cryptography requested in conf but not available')
    return encrypted


def aesgcm_decrypt_password(configuration, encrypted, secret=keyword_auto,
                            init_vector=keyword_auto, aad_stamp=keyword_auto,
                            base64_enc=True):
    """Decrypt AESGCM encrypted password.
    By default the encrypted value includes the Initialization Vector (IV) and
    the Additional Authentication Data (AAD) on a packed base64 encoded form.
    You should not need to override with custom values but it can be done.
    """
    _logger = configuration.logger
    # Based on complete example of securely decrypting with AES GCM from
    # https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption
    if cryptography:
        (iv, crypt, aad) = __aesgcm_unpack_tuple(encrypted, base64_enc)
        if init_vector == keyword_auto:
            init_vector = iv
        if aad_stamp == keyword_auto:
            auth_data = aad
        else:
            auth_data = prepare_aesgcm_aad(configuration, AAD_PREFIX,
                                           aad_stamp)
        key = prepare_aesgcm_key(configuration, secret)
        aesgcm_helper = AESGCM(key)
        password = aesgcm_helper.decrypt(init_vector, crypt, auth_data)
    else:
        _logger.error('decrypt requested without cryptography installed')
        raise Exception('cryptography requested in conf but not available')
    return password


def make_encrypt(configuration, password, secret=keyword_auto, algo="fernet"):
    """Generate an encrypted password. The optional algo argument decides which
    encryption is used.
    """
    if algo.lower() in ("false", ):
        return password
    elif algo.lower() in ("fernet", "safe_encrypt"):
        return fernet_encrypt_password(configuration, password, secret)
    elif algo in ("aesgcm", "aes256_encrypt"):
        return aesgcm_encrypt_password(configuration, password, secret)
    elif algo in ("aesgcm_static", "simple_encrypt"):
        # NOTE: a constant output version of AESGCM relying on a fixed init
        #       vector for each value. Please beware of the potentially reduced
        #       security of this method.
        scrambled_pw = make_scramble(pw, best_crypt_salt(configuration))
        pw_iv = make_safe_hash(scrambled_pw, False)
        return aesgcm_encrypt_password(configuration, password, secret,
                                       init_vector=pw_iv)
    else:
        raise ValueError("Unknown encryption algo: %r" % algo)


def make_decrypt(configuration, encrypted, secret=keyword_auto, algo="fernet"):
    """Decrypt password. The optional algo argument decides which
    encryption is used.
    """
    if algo.lower() in ("false",):
        return encrypted
    elif algo.lower() in ("fernet", "safe_encrypt"):
        return fernet_decrypt_password(configuration, encrypted, secret)
    elif algo in ("aesgcm", "aes256_encrypt", "aesgcm_static",
                  "simple_encrypt"):
        # NOTE: iv and aad are integrated in encrypted value here
        return aesgcm_decrypt_password(configuration, encrypted, secret)
    else:
        raise ValueError("Unknown encryption algo: %r" % algo)


def check_encrypt(configuration, service, username, password, encrypted,
                  secret=keyword_auto, encrypt_cache=None, strict_policy=True,
                  allow_legacy=False, algo="fernet"):
    """Make sure provided password satisfies local password policy and check
    match against existing encrypted password. The optional encrypt_cache
    dictionary argument can be used to cache recent lookups to save time in
    repeated use cases.

    NOTE: we force strict password policy here since we may find weak legacy
    passwords in the user DB and they would easily give full account access.
    The optional boolean allow_legacy argument extends the strict_policy check
    so that passwords matching any configured password legacy policy are also
    accepted. Use only during active log in checks.
    """
    _logger = configuration.logger
    password = force_utf8(password)
    if isinstance(encrypt_cache, dict) and \
            encrypt_cache.get(password, None) == encrypted:
        # print("got cached encrypt: %s" % encrypt_cache.get(password, None))
        return True
    # We check policy AFTER cache lookup since it is already verified for those
    try:
        assure_password_strength(configuration, password, allow_legacy)
    except Exception as exc:
        _logger.warning('%s password for %s does not satisfy local policy: %s'
                        % (service, username, exc))
        if strict_policy:
            return False
    match = (make_encrypt(configuration, password, secret, algo) == encrypted)
    if isinstance(encrypt_cache, dict) and match:
        encrypt_cache[password] = encrypted
        # print("cached digest: %s" % encrypt_cache.get(password, None))
    return match


def assure_reset_supported(configuration, user_dict, auth_type):
    """Make sure auth_type is enabled and configured with a password (hash)
    for user_dict. Raises ValueError if not.
    """
    _logger = configuration.logger
    if not 'password_hash' in user_dict and not 'password' in user_dict:
        _logger.error("cannot generate %s reset token for %s without password"
                      % (auth_type, user_dict['email']))
        raise ValueError("No saved password info for %r !" %
                         user_dict['email'])
    elif auth_type not in configuration.site_login_methods:
        _logger.error("refuse %s reset token not enabled on site: %s" %
                      (auth_type, ', '.join(configuration.site_login_methods)))
        raise ValueError("No %s auth enabled on this site!" % auth_type)
    # NOTE: we only use modern auth field if actually set
    elif auth_type not in user_dict.get('auth', [auth_type]):
        # IMPORTANT: do NOT log credentials
        _logger.error("refuse %s reset token without previous auth: %s" %
                      (auth_type, mask_creds(user_dict)))
        raise ValueError("No %s auth setup for %r!" % (auth_type,
                                                       user_dict['email']))
    return True


def generate_reset_token(configuration, user_dict, auth_type,
                         timestamp=time.time()):
    """Generate a password reset token for user_dict and auth_type. Importantly
    the token must be time limited and encode enough information about the
    current password to help verify that the intended recipient of the token
    should actually be allowed to change the password. This is done by
    embedding a timestamp plus the saved password_hash where applicable and a
    manual hash of the masked password for the user certificate case. The token
    should only be sent to the registered email of the account holder or inlined
    in web forms where the user already authenticated.
    The optional timestamp argument can be used to override the used timestamp
    in cases where operators handle the reset with delay. It defaults to the
    current epoch value if not provided.
    """
    _logger = configuration.logger
    # NOTE: this call may raise ValueError for caller to handle
    assure_reset_supported(configuration, user_dict, auth_type)

    pw_hash = None
    if auth_type in ("migoid", "migoidc"):
        pw_hash = user_dict.get('password_hash', None)
    # Fall back to masked password for cert or no saved hash case
    if auth_type == "migcert" or pw_hash is None:
        pw_hash = make_hash(user_dict.get('password', ''))
    # NOTE: use integer timestamp for simplicity
    token = fernet_encrypt_password(configuration, "%d::%s" % (timestamp,
                                                               pw_hash))
    # IMPORTANT: do NOT log complete token
    _logger.debug("generated %s reset token %r at %r" % (auth_type,
                                                         string_snippet(token),
                                                         timestamp))
    return token


def parse_reset_token(configuration, token, auth_type):
    """Reverse of generate_reset_token used to decode a previously generated
    token into a timestamp and a password hash to match auth_type.
    """
    _logger = configuration.logger
    # IMPORTANT: do NOT log complete token unless invalid
    _logger.debug("parse %s reset token %r" % (auth_type,
                                               string_snippet(token)))
    raw = fernet_decrypt_password(configuration, token)
    parts = raw.split('::', 1)
    # NOTE: the expected decrypted token format is 'int(EPOCH)::PWHASH'
    if not parts[1:] or not parts[0].isdigit():
        _logger.error("cannot parse %s reset token on invalid format: %s" %
                      (auth_type, token))
        raise ValueError("Invalid reset token %r can't be parsed!" % token)
    timestamp, pw_hash = int(parts[0]), parts[1]
    return (timestamp, pw_hash)


def verify_reset_token(configuration, user_dict, token, auth_type,
                       timestamp=int(time.time())):
    """Check that reset token generated from user_dict matches provided token
    from a previous generation. Namely that the parsed password hash matches
    the saved password (hash) and that parsed timestamp is reasonably recent.
    The optional timestamp argument can be used to override the expected
    timestamp in cases where operators handle the reset with delay. It defaults
    to now if not provided.
    """
    _logger = configuration.logger
    # IMPORTANT: do NOT log complete token unless invalid
    _logger.debug("verify %s reset token %r for %r at %d" %
                  (auth_type, string_snippet(token),
                   user_dict['distinguished_name'], timestamp))
    try:
        assure_reset_supported(configuration, user_dict, auth_type)
    except ValueError as vae:
        _logger.warn("verify %s reset token %s failed: %s" % (auth_type, token,
                                                              vae))
        return False

    token_stamp, token_hash = parse_reset_token(configuration, token,
                                                auth_type)
    if token_stamp > timestamp or timestamp - token_stamp > RESET_TOKEN_TTL:
        _logger.debug("reject reset token %r with timestamp %d (%d)" %
                      (token, token_stamp, timestamp))
        return False

    pw_hash = None
    if auth_type in ("migoid", "migoidc"):
        pw_hash = user_dict.get('password_hash', None)
    # Fall back to masked password for cert or no saved hash case
    if auth_type == "migcert" or pw_hash is None:
        pw_hash = make_hash(user_dict.get('password', ''))

    if token_hash != pw_hash:
        # IMPORTANT: do NOT log actual hash but just a snippet hint
        _logger.debug("reject reset token %r with wrong hash: %s vs %s" %
                      (token, string_snippet(token_hash),
                       string_snippet(pw_hash)))
        return False

        # IMPORTANT: do NOT log actual hash but just a snippet hint
    _logger.debug("accept reset token %r with timestamp %d and hash %s" %
                  (string_snippet(token), token_stamp,
                   string_snippet(token_hash)))
    return True


def make_csrf_token(configuration, method, operation, client_id, limit=None):
    """Generate a Cross-Site Request Forgery (CSRF) token to help verify the
    authenticity of user requests. The optional limit argument can be used to
    e.g. put a timestamp into the mix, so that the token automatically expires.
    """
    salt = configuration.site_digest_salt
    merged = "%s:%s:%s:%s" % (method, operation, client_id, limit)
    # configuration.logger.debug("CSRF for %s" % merged)
    xor_id = "%s" % (int(salt, 16) ^ int(b16encode(merged), 16))
    token = make_safe_hash(xor_id)
    return token


def make_csrf_trust_token(configuration, method, operation, args, client_id,
                          limit=None, skip_fields=[]):
    """A special version of the Cross-Site Request Forgery (CSRF) token used
    for cases where we already know the complete query arguments and just need
    to validate that they were passed untampered from us self.
    Packs the query args into the operation in a deterministic order by
    appending in sorted order from args.keys then just applies make_csrf_token.
    The optional skip_fields list can be used to exclude args from the token.
    That is mainly used to allow use for checking where the trust token is
    already part of the args and therefore should not be considered.
    """
    _logger = configuration.logger
    csrf_op = '%s' % operation
    if args:
        sorted_keys = sorted(list(args))
    else:
        sorted_keys = []
    for key in sorted_keys:
        if key in skip_fields:
            continue
        csrf_op += '_%s' % key
        for val in args[key]:
            csrf_op += '_%s' % val
    _logger.debug("made csrf_trust from url %s" % csrf_op)
    return make_csrf_token(configuration, method, csrf_op, client_id, limit)


def password_requirements(site_policy, logger=None):
    """Parse the custom password policy value to get the number of required
    characters and different character classes.
    """
    min_len, min_classes, errors = -1, 42, []
    if site_policy == POLICY_NONE:
        if logger:
            logger.debug('site password policy allows ANY password')
        min_len, min_classes = 0, 0
    elif site_policy == POLICY_WEAK:
        min_len, min_classes = 6, 2
    elif site_policy == POLICY_MEDIUM:
        min_len, min_classes = 8, 3
    elif site_policy == POLICY_HIGH:
        min_len, min_classes = 10, 4
    elif site_policy.startswith(POLICY_MODERN):
        try:
            _, min_len_str = site_policy.split(':', 1)
            min_len, min_classes = int(min_len_str), 1
        except Exception as exc:
            errors.append('modern password policy %s on invalid format: %s' %
                          (site_policy, exc))
    elif site_policy.startswith(POLICY_CUSTOM):
        try:
            _, min_len_str, min_classes_str = site_policy.split(':', 2)
            min_len, min_classes = int(min_len_str), int(min_classes_str)
        except Exception as exc:
            errors.append('custom password policy %s on invalid format: %s' %
                          (site_policy, exc))
    else:
        errors.append('unknown password policy keyword: %s' % site_policy)
    if logger:
        logger.debug('password policy %s requires %d chars from %d classes' %
                     (site_policy, min_len, min_classes))
    return min_len, min_classes, errors


def parse_password_policy(configuration, use_legacy=False):
    """Parse the custom password policy in configuration to get the number of
    required characters and different character classes.
    NOTE: fails hard later if invalid policy is used for best security.
    The optional boolean use_legacy argument results in any configured
    password legacy policy being used instead of the default password policy.
    """
    _logger = configuration.logger
    if use_legacy:
        policy = configuration.site_password_legacy_policy
    else:
        policy = configuration.site_password_policy
    min_len, min_classes, errors = password_requirements(policy, _logger)
    for err in errors:
        _logger.error(err)
    return min_len, min_classes


def __assure_password_strength_helper(configuration, password, use_legacy=False):
    """Helper to check if password fits site password policy or password legacy
    policy in terms of length and required number of different character classes.
    We split into four classes for now, lowercase, uppercase, digits and other.
    The optional use_legacy argument is used to decide if the configured normal
    password policy or any configured password legacy policy should apply.
    """
    _logger = configuration.logger
    if use_legacy:
        policy_fail_msg = 'password does not fit password legacy policy'
    else:
        policy_fail_msg = 'password does not fit password policy'
    min_len, min_classes = parse_password_policy(configuration, use_legacy)
    if min_len < 0 or min_classes > 4:
        raise Exception('parse password policy failed: %d %d (use_legacy: %s)'
                        % (min_len, min_classes, use_legacy))
    if len(password) < min_len:
        raise ValueError('%s: password too short, at least %d chars required' %
                         (policy_fail_msg, min_len))
    char_class_map = {'lower': ascii_lowercase, 'upper': ascii_uppercase,
                      'digits': digits}
    base_chars = ''.join(list(char_class_map.values()))
    pw_classes = []
    for i in password:
        if i not in base_chars and 'other' not in pw_classes:
            pw_classes.append('other')
            continue
        for (char_class, values) in list(char_class_map.items()):
            if i in "%s" % values and not char_class in pw_classes:
                pw_classes.append(char_class)
                break
    if len(pw_classes) < min_classes:
        raise ValueError('%s: password too simple, >= %d char classes required' %
                         (policy_fail_msg, min_classes))
    if configuration.site_password_cracklib:
        if cracklib:
            # NOTE: min_len does not exactly match cracklib.MIN_LENGTH meaning
            #       but we just make sure cracklib does not directly increase
            #       policy requirements.
            cracklib.MIN_LENGTH = min_len + min_classes
            try:
                # NOTE: this raises ValueError if password is too simple
                cracklib.VeryFascistCheck(password)
            except Exception as exc:
                raise ValueError("cracklib refused password: %s" % exc)
        else:
            raise Exception('cracklib requested in conf but not available')
    return True


def assure_password_strength(configuration, password, allow_legacy=False):
    """Make sure password fits site password policy in terms of length and
    required number of different character classes.
    We split into four classes for now, lowercase, uppercase, digits and other.
    The optional allow_legacy argument should be supplied for calls where any
    configured password legacy policy should apply. Namely for cases where only
    an actual password log in is checked, but not when saving a new password
    anywhere.
    """
    _logger = configuration.logger
    site_policy = configuration.site_password_policy
    site_legacy_policy = configuration.site_password_legacy_policy
    try:
        __assure_password_strength_helper(configuration, password, False)
        _logger.debug('password compliant with password policy (%s)' %
                      site_policy)
        return True
    except ValueError as err:
        if site_legacy_policy and allow_legacy:
            _logger.info("%s. Proceed with legacy policy check." % err)
        else:
            _logger.warning("%s" % err)
            raise err

    try:
        __assure_password_strength_helper(configuration, password, True)
        _logger.debug('password compliant with password legacy policy (%s)' %
                      site_legacy_policy)
        return True
    except ValueError as err:
        _logger.warning("%s" % err)
        raise err


def valid_login_password(configuration, password):
    """Helper to verify that provided password is valid for login purposes.
    This is a convenience wrapper for assure_password_strength to get a boolean
    result. Used in grid_webdavs and from sftpsubsys PAM helper.
    """
    _logger = configuration.logger
    try:
        assure_password_strength(configuration, password, allow_legacy=True)
        return True
    except ValueError as err:
        return False
    except Exception as exc:
        _logger.error("unexpected exception in valid_login_password: %s" % exc)
        return False


def make_generic_hash(val, algo, hex_format=True):
    """Generate a hash for val using requested algo and return the 2*N-char
    hexdigest if hex_format is set (default) or the corresponding raw N bytes
    otherwise.
    """
    if not algo in valid_hash_algos:
        algo = 'md5'
    hash_helper = valid_hash_algos[algo]
    if hex_format:
        return hash_helper(val).hexdigest()
    else:
        return hash_helper(val).digest()


def make_simple_hash(val, hex_format=True):
    """Generate a simple md5 hash for val and return the 32-char hexdigest if
    the default hex_format is set or the corresponding raw 16 bytes otherwise.
    """
    return make_generic_hash(val, 'md5', hex_format)


def make_safe_hash(val, hex_format=True):
    """Generate a safe sha256 hash for val and return the 64-char hexdigest if
    the default hex_format is set or the corresponding raw 32 bytes otherwise.
    """
    return make_generic_hash(val, 'sha256', hex_format)


def make_path_hash(configuration, path):
    """Generate a 128-bit md5 hash for path and return the 32 char hexdigest.
    Used to compress long paths into a fixed length string ID without
    introducing serious collision risks, under the assumption that the
    total number of path hashes is say in the millions or less. Please refer
    to the collision risk calculations at e.g
    http://preshing.com/20110504/hash-collision-probabilities/
    https://en.wikipedia.org/wiki/Birthday_attack
    for the details.
    """
    _logger = configuration.logger
    _logger.debug("make path hash for %s" % path)
    return make_simple_hash(path)


def generate_random_ascii(count, charset):
    """Generate a string of count random characters from given charset"""
    return ''.join(SystemRandom().choice(charset) for _ in range(count))


def generate_random_password(configuration, tries=42):
    """Generate a password string of random characters from allowed password
    charset and taking any active password policy in configuration into
    account.
    Tries can be used to tune the number of attempts to make sure random
    selection does not yield too weak a password.
    """
    _logger = configuration.logger
    count, classes = parse_password_policy(configuration)
    # TODO: use the password charset from safeinput instead?
    charset = ascii_lowercase
    if classes > 1:
        charset += ascii_uppercase
    if classes > 2:
        charset += digits
    if classes > 3:
        charset += ',.;:+=&%#@£$/?*'
    for i in range(tries):
        _logger.debug("make password with %d chars from %s" % (count, charset))
        password = generate_random_ascii(count, charset)
        try:
            assure_password_strength(configuration, password)
            return password
        except ValueError as err:
            _logger.warning("generated password %s didn't fit policy - retry"
                            % password)
            pass
    _logger.error("failed to generate password to fit site policy")
    raise ValueError("Failed to generate suitable password!")


if __name__ == "__main__":
    from mig.shared.conf import get_configuration_object
    configuration = get_configuration_object()
    dummy_user = {'distinguished_name': 'Test User', 'password_hash': ''}
    pw_tests = (
        '', 'abc', 'dbey3h', 'abcdefgh', '12345678', 'test1234',
        'password', 'djeudmdj', 'Password12', 'P4s5W0rd',
        'GoofBall', 'b43kdn22', 'Dr3Ab3_2', 'kasd#D2s',
        'fsk34dsa-.32d', 'd3kk3mdkkded', 'Loh/p4iv,ahk',
        'MinimumIntrusionGrid', 'correcthorsebatterystaple'
    )
    for pw in pw_tests:
        for policy in PASSWORD_POLICIES:
            if policy == POLICY_MODERN:
                policy += ':12'
            elif policy == POLICY_CUSTOM:
                policy += ':12:4'

            configuration.site_password_policy = policy
            try:
                res = assure_password_strength(configuration, pw)
            except Exception as exc:
                res = "False (%s)" % exc
            print("Password %r follows %s password policy: %s" %
                  (pw, policy, res))

        decrypted = None
        hashed = make_hash(pw)
        snippet = string_snippet(hashed)
        dummy_user['password_hash'] = hashed
        token = generate_reset_token(configuration, dummy_user, 'migoid')
        print("Password %r gives hash %r, snippet %r and reset token %r" %
              (pw, hashed, snippet, token))
        try:
            # print("Fernet encrypt password %r" % pw)
            encrypted = fernet_encrypt_password(configuration, pw)
            # print("Decrypt Fernet encrypted password %r" % encrypted)
            decrypted = fernet_decrypt_password(configuration, encrypted)
            # print("Password %r encrypted to %s and decrypted to %s ." %
            #      (pw, encrypted, decrypted))
            if pw != decrypted:
                raise ValueError("Password enc+dec corruption: %r vs %r" %
                                 (pw, decrypted))
            print("Password %r fernet encrypted and decrypted correctly (%r)" %
                  (pw, encrypted))
        except Exception as exc:
            print("Failed to handle fernet encrypt/decrypt %s : %s" %
                  (pw, exc))

        try:
            # print("AESGCM encrypt password %r" % pw)
            encrypted = aesgcm_encrypt_password(configuration, pw)
            # print("Decrypt AESGCM encrypted password %r" % encrypted)
            decrypted = aesgcm_decrypt_password(configuration, encrypted)
            # print("Password %r encrypted to %s and decrypted to %r" %
            #      (pw, encrypted, decrypted))
            if pw != decrypted:
                raise ValueError("Password enc+dec corruption: %r vs %r" %
                                 (pw, decrypted))
            print("Password %r aesgcm encrypted and decrypted correctly (%r)" %
                  (pw, encrypted))
        except Exception as exc:
            print("Failed to handle aesgcm encrypt/decrypt %s : %s" %
                  (pw, exc))

        try:
            static_iv = prepare_aesgcm_iv(
                configuration, iv_entropy=make_safe_hash(pw, False))
            # print("AESGCM static encrypt password %r with iv %r" %
            #      (pw, pw_iv))
            encrypted = aesgcm_encrypt_password(configuration, pw,
                                                init_vector=static_iv)
            # print("Decrypt AESGCM static encrypted password %r" % encrypted)
            decrypted = aesgcm_decrypt_password(configuration, encrypted,
                                                init_vector=static_iv)
            # print("Password %r static encrypted to %s and decrypted to %r" %
            #      (pw, encrypted, decrypted))
            if pw != decrypted:
                raise ValueError("Password static enc+dec corruption: %r vs %r" %
                                 (pw, decrypted))
            print("Password %r aesgcm-static encrypted and decrypted correctly (%r)" %
                  (pw, encrypted))
        except Exception as exc:
            print(
                "Failed to handle aesgcm static encrypt/decrypt %s : %s" % (pw, exc))
