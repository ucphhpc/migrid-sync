#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# d3des - [optionally add short module description on this line]
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

###
### MIG PROXY - d3des.py
### Simon A. F. Lund - safl@safl.dk
###
### THis module is taken from the pyvnc2swf project, there have been some minor
### changes:
###
### - added the convenience function decrypt_response
### - added the convenience function verify_response
### - renamed the variable challange to challenge
###

##
##  pyvnc2swf - d3des.py
##
##  $Id: d3des.py,v 1.1 2007/04/25 16:55:25 euske Exp $
##
##  Copyright (C) 2007 by Yusuke Shinyama (yusuke at cs . nyu . edu)
##  All Rights Reserved.
##
##  This is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This software is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this software; if not, write to the Free Software
##  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307,
##  USA.
##

#  The following code is derived from vncviewer/rfb/d3des.c (GPL).

#  This is D3DES (V5.09) by Richard Outerbridge with the double and
#  triple-length support removed for use in VNC.  Also the bytebit[] array
#  has been reversed so that the most significant bit in each byte of the
#  key is ignored, not the least significant.
#
#  These changes are:
#   Copyright (C) 1999 AT&T Laboratories Cambridge.  All Rights Reserved.
#
#  This software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#
#  D3DES (V5.09) -
#
#  A portable, public domain, version of the Data Encryption Standard.
#
#  Written with Symantec's THINK (Lightspeed) C by Richard Outerbridge.
#  Thanks to: Dan Hoey for his excellent Initial and Inverse permutation
#  code;  Jim Gillogly & Phil Karn for the DES key schedule code; Dennis
#  Ferguson, Eric Young and Dana How for comparing notes; and Ray Lau,
#  for humouring me on.
#
#  Copyright (c) 1988,1989,1990,1991,1992 by Richard Outerbridge.
#  (GEnie : OUTER; CIS : [71755,204]) Graven Imagery, 1992.
#

from __future__ import print_function
from builtins import range
from struct import pack, unpack

bytebit = [
    0o1,
    0o2,
    0o4,
    0o10,
    0o20,
    0o40,
    0o100,
    0o200,
    ]

bigbyte = [
    8388608,
    4194304,
    2097152,
    1048576,
    524288,
    262144,
    131072,
    65536,
    32768,
    16384,
    8192,
    4096,
    2048,
    1024,
    512,
    256,
    128,
    64,
    32,
    16,
    8,
    4,
    2,
    1,
    ]

# Use the key schedule specified in the Standard (ANSI X3.92-1981).

pc1 = [
    56,
    48,
    40,
    0o40,
    24,
    0o20,
    0o10,
    0,
    57,
    49,
    41,
    33,
    25,
    17,
    9,
    0o1,
    58,
    50,
    42,
    34,
    26,
    18,
    10,
    0o2,
    59,
    51,
    43,
    35,
    62,
    54,
    46,
    38,
    30,
    22,
    14,
    6,
    61,
    53,
    45,
    37,
    29,
    21,
    13,
    5,
    60,
    52,
    44,
    36,
    28,
    20,
    12,
    0o4,
    27,
    19,
    11,
    3,
    ]

totrot = [
    0o1,
    0o2,
    0o4,
    6,
    0o10,
    10,
    12,
    14,
    15,
    17,
    19,
    21,
    23,
    25,
    27,
    28,
    ]

pc2 = [
    13,
    0o20,
    10,
    23,
    0,
    0o4,
    0o2,
    27,
    14,
    5,
    20,
    9,
    22,
    18,
    11,
    3,
    25,
    0o7,
    15,
    6,
    26,
    19,
    12,
    0o1,
    40,
    51,
    30,
    36,
    46,
    54,
    29,
    39,
    50,
    44,
    0o40,
    47,
    43,
    48,
    38,
    55,
    33,
    52,
    45,
    41,
    49,
    35,
    28,
    31,
    ]


def deskey(key, decrypt):  # Thanks to James Gillogly & Phil Karn!
    key = unpack('8B', key)

    pc1m = [0] * 56
    pcr = [0] * 56
    kn = [0x00000000] * 0o40

    for j in range(56):
        l = pc1[j]
        m = l & 0o7
        if key[l >> 3] & bytebit[m]:
            pc1m[j] = 0o1
        else:
            pc1m[j] = 0

    for i in range(0o20):
        if decrypt:
            m = 15 - i << 0o1
        else:
            m = i << 0o1
        n = m + 0o1
        kn[m] = kn[n] = 0x00000000
        for j in range(28):
            l = j + totrot[i]
            if l < 28:
                pcr[j] = pc1m[l]
            else:
                pcr[j] = pc1m[l - 28]
        for j in range(28, 56):
            l = j + totrot[i]
            if l < 56:
                pcr[j] = pc1m[l]
            else:
                pcr[j] = pc1m[l - 28]
        for j in range(24):
            if pcr[pc2[j]]:
                kn[m] |= bigbyte[j]
            if pcr[pc2[j + 24]]:
                kn[n] |= bigbyte[j]

    return cookey(kn)


def cookey(raw):
    key = []
    for i in range(0, 0o40, 0o2):
        (raw0, raw1) = (raw[i], raw[i + 0o1])
        k = (raw0 & 0x00fc0000) << 6
        k |= (raw0 & 0x00000fc0) << 10
        k |= (raw1 & 0x00fc0000) >> 10
        k |= (raw1 & 0x00000fc0) >> 6
        key.append(k)
        k = (raw0 & 0x0003f000) << 12
        k |= (raw0 & 63) << 0o20
        k |= (raw1 & 0x0003f000) >> 0o4
        k |= raw1 & 63
        key.append(k)
    return key


SP1 = [
    0x01010400,
    0x00000000,
    65536,
    0x01010404,
    0x01010004,
    0x00010404,
    4,
    65536,
    1024,
    0x01010400,
    0x01010404,
    1024,
    0x01000404,
    0x01010004,
    0x01000000,
    4,
    0x00000404,
    0x01000400,
    0x01000400,
    0x00010400,
    0x00010400,
    0x01010000,
    0x01010000,
    0x01000404,
    0x00010004,
    0x01000004,
    0x01000004,
    0x00010004,
    0x00000000,
    0x00000404,
    0x00010404,
    0x01000000,
    65536,
    0x01010404,
    4,
    0x01010000,
    0x01010400,
    0x01000000,
    0x01000000,
    1024,
    0x01010004,
    65536,
    0x00010400,
    0x01000004,
    1024,
    4,
    0x01000404,
    0x00010404,
    0x01010404,
    0x00010004,
    0x01010000,
    0x01000404,
    0x01000004,
    0x00000404,
    0x00010404,
    0x01010400,
    0x00000404,
    0x01000400,
    0x01000400,
    0x00000000,
    0x00010004,
    0x00010400,
    0x00000000,
    0x01010004,
    ]

SP2 = [
    0x80108020,
    0x80008000,
    32768,
    0x00108020,
    1048576,
    32,
    0x80100020,
    0x80008020,
    0x80000020,
    0x80108020,
    0x80108000,
    0x80000000,
    0x80008000,
    1048576,
    32,
    0x80100020,
    0x00108000,
    0x00100020,
    0x80008020,
    0x00000000,
    0x80000000,
    32768,
    0x00108020,
    0x80100000,
    0x00100020,
    0x80000020,
    0x00000000,
    0x00108000,
    0x00008020,
    0x80108000,
    0x80100000,
    0x00008020,
    0x00000000,
    0x00108020,
    0x80100020,
    1048576,
    0x80008020,
    0x80100000,
    0x80108000,
    32768,
    0x80100000,
    0x80008000,
    32,
    0x80108020,
    0x00108020,
    32,
    32768,
    0x80000000,
    0x00008020,
    0x80108000,
    1048576,
    0x80000020,
    0x00100020,
    0x80008020,
    0x80000020,
    0x00100020,
    0x00108000,
    0x00000000,
    0x80008000,
    0x00008020,
    0x80000000,
    0x80100020,
    0x80108020,
    0x00108000,
    ]

SP3 = [
    0x00000208,
    0x08020200,
    0x00000000,
    0x08020008,
    0x08000200,
    0x00000000,
    0x00020208,
    0x08000200,
    0x00020008,
    0x08000008,
    0x08000008,
    131072,
    0x08020208,
    0x00020008,
    0x08020000,
    0x00000208,
    0x08000000,
    8,
    0x08020200,
    512,
    0x00020200,
    0x08020000,
    0x08020008,
    0x00020208,
    0x08000208,
    0x00020200,
    131072,
    0x08000208,
    8,
    0x08020208,
    512,
    0x08000000,
    0x08020200,
    0x08000000,
    0x00020008,
    0x00000208,
    131072,
    0x08020200,
    0x08000200,
    0x00000000,
    512,
    0x00020008,
    0x08020208,
    0x08000200,
    0x08000008,
    512,
    0x00000000,
    0x08020008,
    0x08000208,
    131072,
    0x08000000,
    0x08020208,
    8,
    0x00020208,
    0x00020200,
    0x08000008,
    0x08020000,
    0x08000208,
    0x00000208,
    0x08020000,
    0x00020208,
    8,
    0x08020008,
    0x00020200,
    ]

SP4 = [
    0x00802001,
    0x00002081,
    0x00002081,
    128,
    0x00802080,
    0x00800081,
    0x00800001,
    0x00002001,
    0x00000000,
    0x00802000,
    0x00802000,
    0x00802081,
    0x00000081,
    0x00000000,
    0x00800080,
    0x00800001,
    1,
    8192,
    8388608,
    0x00802001,
    128,
    8388608,
    0x00002001,
    0x00002080,
    0x00800081,
    1,
    0x00002080,
    0x00800080,
    8192,
    0x00802080,
    0x00802081,
    0x00000081,
    0x00800080,
    0x00800001,
    0x00802000,
    0x00802081,
    0x00000081,
    0x00000000,
    0x00000000,
    0x00802000,
    0x00002080,
    0x00800080,
    0x00800081,
    1,
    0x00802001,
    0x00002081,
    0x00002081,
    128,
    0x00802081,
    0x00000081,
    1,
    8192,
    0x00800001,
    0x00002001,
    0x00802080,
    0x00800081,
    0x00002001,
    0x00002080,
    8388608,
    0x00802001,
    128,
    8388608,
    8192,
    0x00802080,
    ]

SP5 = [
    256,
    0x02080100,
    0x02080000,
    0x42000100,
    524288,
    256,
    0x40000000,
    0x02080000,
    0x40080100,
    524288,
    0x02000100,
    0x40080100,
    0x42000100,
    0x42080000,
    0x00080100,
    0x40000000,
    0x02000000,
    0x40080000,
    0x40080000,
    0x00000000,
    0x40000100,
    0x42080100,
    0x42080100,
    0x02000100,
    0x42080000,
    0x40000100,
    0x00000000,
    0x42000000,
    0x02080100,
    0x02000000,
    0x42000000,
    0x00080100,
    524288,
    0x42000100,
    256,
    0x02000000,
    0x40000000,
    0x02080000,
    0x42000100,
    0x40080100,
    0x02000100,
    0x40000000,
    0x42080000,
    0x02080100,
    0x40080100,
    256,
    0x02000000,
    0x42080000,
    0x42080100,
    0x00080100,
    0x42000000,
    0x42080100,
    0x02080000,
    0x00000000,
    0x40080000,
    0x42000000,
    0x00080100,
    0x02000100,
    0x40000100,
    524288,
    0x00000000,
    0x40080000,
    0x02080100,
    0x40000100,
    ]

SP6 = [
    0x20000010,
    0x20400000,
    16384,
    0x20404010,
    0x20400000,
    16,
    0x20404010,
    4194304,
    0x20004000,
    0x00404010,
    4194304,
    0x20000010,
    0x00400010,
    0x20004000,
    0x20000000,
    0x00004010,
    0x00000000,
    0x00400010,
    0x20004010,
    16384,
    0x00404000,
    0x20004010,
    16,
    0x20400010,
    0x20400010,
    0x00000000,
    0x00404010,
    0x20404000,
    0x00004010,
    0x00404000,
    0x20404000,
    0x20000000,
    0x20004000,
    16,
    0x20400010,
    0x00404000,
    0x20404010,
    4194304,
    0x00004010,
    0x20000010,
    4194304,
    0x20004000,
    0x20000000,
    0x00004010,
    0x20000010,
    0x20404010,
    0x00404000,
    0x20400000,
    0x00404010,
    0x20404000,
    0x00000000,
    0x20400010,
    16,
    16384,
    0x20400000,
    0x00404010,
    16384,
    0x00400010,
    0x20004010,
    0x00000000,
    0x20404000,
    0x20000000,
    0x00400010,
    0x20004010,
    ]

SP7 = [
    2097152,
    0x04200002,
    0x04000802,
    0x00000000,
    2048,
    0x04000802,
    0x00200802,
    0x04200800,
    0x04200802,
    2097152,
    0x00000000,
    0x04000002,
    2,
    0x04000000,
    0x04200002,
    0x00000802,
    0x04000800,
    0x00200802,
    0x00200002,
    0x04000800,
    0x04000002,
    0x04200000,
    0x04200800,
    0x00200002,
    0x04200000,
    2048,
    0x00000802,
    0x04200802,
    0x00200800,
    2,
    0x04000000,
    0x00200800,
    0x04000000,
    0x00200800,
    2097152,
    0x04000802,
    0x04000802,
    0x04200002,
    0x04200002,
    2,
    0x00200002,
    0x04000000,
    0x04000800,
    2097152,
    0x04200800,
    0x00000802,
    0x00200802,
    0x04200800,
    0x00000802,
    0x04000002,
    0x04200802,
    0x04200000,
    0x00200800,
    0x00000000,
    2,
    0x04200802,
    0x00000000,
    0x00200802,
    0x04200000,
    2048,
    0x04000002,
    0x04000800,
    2048,
    0x00200002,
    ]

SP8 = [
    0x10001040,
    4096,
    262144,
    0x10041040,
    0x10000000,
    0x10001040,
    64,
    0x10000000,
    0x00040040,
    0x10040000,
    0x10041040,
    0x00041000,
    0x10041000,
    0x00041040,
    4096,
    64,
    0x10040000,
    0x10000040,
    0x10001000,
    0x00001040,
    0x00041000,
    0x00040040,
    0x10040040,
    0x10041000,
    0x00001040,
    0x00000000,
    0x00000000,
    0x10040040,
    0x10000040,
    0x10001000,
    0x00041040,
    262144,
    0x00041040,
    262144,
    0x10041000,
    4096,
    64,
    0x10040040,
    4096,
    0x00041040,
    0x10001000,
    64,
    0x10000040,
    0x10040000,
    0x10040040,
    0x10000000,
    262144,
    0x10001040,
    0x00000000,
    0x10041040,
    0x00040040,
    0x10000040,
    0x10040000,
    0x10001000,
    0x10001040,
    0x00000000,
    0x10041040,
    0x00041000,
    0x00041000,
    0x00001040,
    0x00001040,
    0x00040040,
    0x10000000,
    0x10041000,
    ]


def desfunc(block, keys):
    (leftt, right) = unpack('>II', block)

    work = (leftt >> 0o4 ^ right) & 0x0f0f0f0f
    right ^= work
    leftt ^= work << 0o4
    work = (leftt >> 0o20 ^ right) & 0x0000ffff
    right ^= work
    leftt ^= work << 0o20
    work = (right >> 0o2 ^ leftt) & 0x33333333
    leftt ^= work
    right ^= work << 0o2
    work = (right >> 0o10 ^ leftt) & 0x00ff00ff
    leftt ^= work
    right ^= work << 0o10
    right = (right << 0o1 | right >> 31 & 1) & 0xffffffff
    work = (leftt ^ right) & 0xaaaaaaaa
    leftt ^= work
    right ^= work
    leftt = (leftt << 0o1 | leftt >> 31 & 1) & 0xffffffff

    for i in range(0, 0o40, 0o4):
        work = right << 28 | right >> 0o4
        work ^= keys[i]
        fval = SP7[work & 63]
        fval |= SP5[work >> 0o10 & 63]
        fval |= SP3[work >> 0o20 & 63]
        fval |= SP1[work >> 24 & 63]
        work = right ^ keys[i + 0o1]
        fval |= SP8[work & 63]
        fval |= SP6[work >> 0o10 & 63]
        fval |= SP4[work >> 0o20 & 63]
        fval |= SP2[work >> 24 & 63]
        leftt ^= fval
        work = leftt << 28 | leftt >> 0o4
        work ^= keys[i + 0o2]
        fval = SP7[work & 63]
        fval |= SP5[work >> 0o10 & 63]
        fval |= SP3[work >> 0o20 & 63]
        fval |= SP1[work >> 24 & 63]
        work = leftt ^ keys[i + 3]
        fval |= SP8[work & 63]
        fval |= SP6[work >> 0o10 & 63]
        fval |= SP4[work >> 0o20 & 63]
        fval |= SP2[work >> 24 & 63]
        right ^= fval

    right = right << 31 | right >> 0o1
    work = (leftt ^ right) & 0xaaaaaaaa
    leftt ^= work
    right ^= work
    leftt = leftt << 31 | leftt >> 0o1
    work = (leftt >> 0o10 ^ right) & 0x00ff00ff
    right ^= work
    leftt ^= work << 0o10
    work = (leftt >> 0o2 ^ right) & 0x33333333
    right ^= work
    leftt ^= work << 0o2
    work = (right >> 0o20 ^ leftt) & 0x0000ffff
    leftt ^= work
    right ^= work << 0o20
    work = (right >> 0o4 ^ leftt) & 0x0f0f0f0f
    leftt ^= work
    right ^= work << 0o4

    leftt &= 0xffffffff
    right &= 0xffffffff
    return pack('>II', right, leftt)


# from vncviewer/rfb/vncauth.c:

fixedkey = [
    23,
    82,
    107,
    6,
    35,
    78,
    88,
    0o7,
    ]


def decrypt_passwd(data):
    dk = deskey(pack('8B', *fixedkey), True)
    return desfunc(data, dk)


def generate_response(passwd, challenge):
    ek = deskey((passwd + '\x00' * 0o10)[:0o10], False)
    return desfunc(challenge[:0o10], ek) + desfunc(challenge[0o10:], ek)


def decrypt_response(passwd, encryptedChallenge):
    dk = deskey((passwd + '\x00' * 0o10)[:0o10], True)
    return desfunc(encryptedChallenge[:0o10], dk) \
        + desfunc(encryptedChallenge[0o10:], dk)


def verify_response(passwd, encryptedChallenge, challenge):
    return decrypt_response(passwd, encryptedChallenge) == challenge


# test

if __name__ == '__main__':
    key = 'test1234'
    plain = 'hello321'
    cipher = '\xb4f\x01UnZ1\t'
    ek = deskey(key, False)
    dk = deskey(key, True)
    assert desfunc(plain, ek) == cipher
    assert desfunc(desfunc(plain, ek), dk) == plain
    assert desfunc(desfunc(plain, dk), ek) == plain
    print('test succeeded.')
