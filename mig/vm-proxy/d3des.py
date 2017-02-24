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

from struct import pack, unpack

bytebit = [
    01,
    02,
    04,
    010,
    020,
    040,
    0100,
    0200,
    ]

bigbyte = [
    8388608L,
    4194304L,
    2097152L,
    1048576L,
    524288L,
    262144L,
    131072L,
    65536L,
    32768L,
    16384L,
    8192L,
    4096L,
    2048L,
    1024L,
    512L,
    256L,
    128L,
    64L,
    32L,
    16L,
    8L,
    4L,
    2L,
    1L,
    ]

# Use the key schedule specified in the Standard (ANSI X3.92-1981).

pc1 = [
    56,
    48,
    40,
    040,
    24,
    020,
    010,
    0,
    57,
    49,
    41,
    33,
    25,
    17,
    9,
    01,
    58,
    50,
    42,
    34,
    26,
    18,
    10,
    02,
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
    04,
    27,
    19,
    11,
    3,
    ]

totrot = [
    01,
    02,
    04,
    6,
    010,
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
    020,
    10,
    23,
    0,
    04,
    02,
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
    07,
    15,
    6,
    26,
    19,
    12,
    01,
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
    040,
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
    kn = [0x00000000L] * 040

    for j in range(56):
        l = pc1[j]
        m = l & 07
        if key[l >> 3] & bytebit[m]:
            pc1m[j] = 01
        else:
            pc1m[j] = 0

    for i in range(020):
        if decrypt:
            m = 15 - i << 01
        else:
            m = i << 01
        n = m + 01
        kn[m] = kn[n] = 0x00000000L
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
    for i in range(0, 040, 02):
        (raw0, raw1) = (raw[i], raw[i + 01])
        k = (raw0 & 0x00fc0000L) << 6
        k |= (raw0 & 0x00000fc0L) << 10
        k |= (raw1 & 0x00fc0000L) >> 10
        k |= (raw1 & 0x00000fc0L) >> 6
        key.append(k)
        k = (raw0 & 0x0003f000L) << 12
        k |= (raw0 & 63L) << 020
        k |= (raw1 & 0x0003f000L) >> 04
        k |= raw1 & 63L
        key.append(k)
    return key


SP1 = [
    0x01010400L,
    0x00000000L,
    65536L,
    0x01010404L,
    0x01010004L,
    0x00010404L,
    4L,
    65536L,
    1024L,
    0x01010400L,
    0x01010404L,
    1024L,
    0x01000404L,
    0x01010004L,
    0x01000000L,
    4L,
    0x00000404L,
    0x01000400L,
    0x01000400L,
    0x00010400L,
    0x00010400L,
    0x01010000L,
    0x01010000L,
    0x01000404L,
    0x00010004L,
    0x01000004L,
    0x01000004L,
    0x00010004L,
    0x00000000L,
    0x00000404L,
    0x00010404L,
    0x01000000L,
    65536L,
    0x01010404L,
    4L,
    0x01010000L,
    0x01010400L,
    0x01000000L,
    0x01000000L,
    1024L,
    0x01010004L,
    65536L,
    0x00010400L,
    0x01000004L,
    1024L,
    4L,
    0x01000404L,
    0x00010404L,
    0x01010404L,
    0x00010004L,
    0x01010000L,
    0x01000404L,
    0x01000004L,
    0x00000404L,
    0x00010404L,
    0x01010400L,
    0x00000404L,
    0x01000400L,
    0x01000400L,
    0x00000000L,
    0x00010004L,
    0x00010400L,
    0x00000000L,
    0x01010004L,
    ]

SP2 = [
    0x80108020L,
    0x80008000L,
    32768L,
    0x00108020L,
    1048576L,
    32L,
    0x80100020L,
    0x80008020L,
    0x80000020L,
    0x80108020L,
    0x80108000L,
    0x80000000L,
    0x80008000L,
    1048576L,
    32L,
    0x80100020L,
    0x00108000L,
    0x00100020L,
    0x80008020L,
    0x00000000L,
    0x80000000L,
    32768L,
    0x00108020L,
    0x80100000L,
    0x00100020L,
    0x80000020L,
    0x00000000L,
    0x00108000L,
    0x00008020L,
    0x80108000L,
    0x80100000L,
    0x00008020L,
    0x00000000L,
    0x00108020L,
    0x80100020L,
    1048576L,
    0x80008020L,
    0x80100000L,
    0x80108000L,
    32768L,
    0x80100000L,
    0x80008000L,
    32L,
    0x80108020L,
    0x00108020L,
    32L,
    32768L,
    0x80000000L,
    0x00008020L,
    0x80108000L,
    1048576L,
    0x80000020L,
    0x00100020L,
    0x80008020L,
    0x80000020L,
    0x00100020L,
    0x00108000L,
    0x00000000L,
    0x80008000L,
    0x00008020L,
    0x80000000L,
    0x80100020L,
    0x80108020L,
    0x00108000L,
    ]

SP3 = [
    0x00000208L,
    0x08020200L,
    0x00000000L,
    0x08020008L,
    0x08000200L,
    0x00000000L,
    0x00020208L,
    0x08000200L,
    0x00020008L,
    0x08000008L,
    0x08000008L,
    131072L,
    0x08020208L,
    0x00020008L,
    0x08020000L,
    0x00000208L,
    0x08000000L,
    8L,
    0x08020200L,
    512L,
    0x00020200L,
    0x08020000L,
    0x08020008L,
    0x00020208L,
    0x08000208L,
    0x00020200L,
    131072L,
    0x08000208L,
    8L,
    0x08020208L,
    512L,
    0x08000000L,
    0x08020200L,
    0x08000000L,
    0x00020008L,
    0x00000208L,
    131072L,
    0x08020200L,
    0x08000200L,
    0x00000000L,
    512L,
    0x00020008L,
    0x08020208L,
    0x08000200L,
    0x08000008L,
    512L,
    0x00000000L,
    0x08020008L,
    0x08000208L,
    131072L,
    0x08000000L,
    0x08020208L,
    8L,
    0x00020208L,
    0x00020200L,
    0x08000008L,
    0x08020000L,
    0x08000208L,
    0x00000208L,
    0x08020000L,
    0x00020208L,
    8L,
    0x08020008L,
    0x00020200L,
    ]

SP4 = [
    0x00802001L,
    0x00002081L,
    0x00002081L,
    128L,
    0x00802080L,
    0x00800081L,
    0x00800001L,
    0x00002001L,
    0x00000000L,
    0x00802000L,
    0x00802000L,
    0x00802081L,
    0x00000081L,
    0x00000000L,
    0x00800080L,
    0x00800001L,
    1L,
    8192L,
    8388608L,
    0x00802001L,
    128L,
    8388608L,
    0x00002001L,
    0x00002080L,
    0x00800081L,
    1L,
    0x00002080L,
    0x00800080L,
    8192L,
    0x00802080L,
    0x00802081L,
    0x00000081L,
    0x00800080L,
    0x00800001L,
    0x00802000L,
    0x00802081L,
    0x00000081L,
    0x00000000L,
    0x00000000L,
    0x00802000L,
    0x00002080L,
    0x00800080L,
    0x00800081L,
    1L,
    0x00802001L,
    0x00002081L,
    0x00002081L,
    128L,
    0x00802081L,
    0x00000081L,
    1L,
    8192L,
    0x00800001L,
    0x00002001L,
    0x00802080L,
    0x00800081L,
    0x00002001L,
    0x00002080L,
    8388608L,
    0x00802001L,
    128L,
    8388608L,
    8192L,
    0x00802080L,
    ]

SP5 = [
    256L,
    0x02080100L,
    0x02080000L,
    0x42000100L,
    524288L,
    256L,
    0x40000000L,
    0x02080000L,
    0x40080100L,
    524288L,
    0x02000100L,
    0x40080100L,
    0x42000100L,
    0x42080000L,
    0x00080100L,
    0x40000000L,
    0x02000000L,
    0x40080000L,
    0x40080000L,
    0x00000000L,
    0x40000100L,
    0x42080100L,
    0x42080100L,
    0x02000100L,
    0x42080000L,
    0x40000100L,
    0x00000000L,
    0x42000000L,
    0x02080100L,
    0x02000000L,
    0x42000000L,
    0x00080100L,
    524288L,
    0x42000100L,
    256L,
    0x02000000L,
    0x40000000L,
    0x02080000L,
    0x42000100L,
    0x40080100L,
    0x02000100L,
    0x40000000L,
    0x42080000L,
    0x02080100L,
    0x40080100L,
    256L,
    0x02000000L,
    0x42080000L,
    0x42080100L,
    0x00080100L,
    0x42000000L,
    0x42080100L,
    0x02080000L,
    0x00000000L,
    0x40080000L,
    0x42000000L,
    0x00080100L,
    0x02000100L,
    0x40000100L,
    524288L,
    0x00000000L,
    0x40080000L,
    0x02080100L,
    0x40000100L,
    ]

SP6 = [
    0x20000010L,
    0x20400000L,
    16384L,
    0x20404010L,
    0x20400000L,
    16L,
    0x20404010L,
    4194304L,
    0x20004000L,
    0x00404010L,
    4194304L,
    0x20000010L,
    0x00400010L,
    0x20004000L,
    0x20000000L,
    0x00004010L,
    0x00000000L,
    0x00400010L,
    0x20004010L,
    16384L,
    0x00404000L,
    0x20004010L,
    16L,
    0x20400010L,
    0x20400010L,
    0x00000000L,
    0x00404010L,
    0x20404000L,
    0x00004010L,
    0x00404000L,
    0x20404000L,
    0x20000000L,
    0x20004000L,
    16L,
    0x20400010L,
    0x00404000L,
    0x20404010L,
    4194304L,
    0x00004010L,
    0x20000010L,
    4194304L,
    0x20004000L,
    0x20000000L,
    0x00004010L,
    0x20000010L,
    0x20404010L,
    0x00404000L,
    0x20400000L,
    0x00404010L,
    0x20404000L,
    0x00000000L,
    0x20400010L,
    16L,
    16384L,
    0x20400000L,
    0x00404010L,
    16384L,
    0x00400010L,
    0x20004010L,
    0x00000000L,
    0x20404000L,
    0x20000000L,
    0x00400010L,
    0x20004010L,
    ]

SP7 = [
    2097152L,
    0x04200002L,
    0x04000802L,
    0x00000000L,
    2048L,
    0x04000802L,
    0x00200802L,
    0x04200800L,
    0x04200802L,
    2097152L,
    0x00000000L,
    0x04000002L,
    2L,
    0x04000000L,
    0x04200002L,
    0x00000802L,
    0x04000800L,
    0x00200802L,
    0x00200002L,
    0x04000800L,
    0x04000002L,
    0x04200000L,
    0x04200800L,
    0x00200002L,
    0x04200000L,
    2048L,
    0x00000802L,
    0x04200802L,
    0x00200800L,
    2L,
    0x04000000L,
    0x00200800L,
    0x04000000L,
    0x00200800L,
    2097152L,
    0x04000802L,
    0x04000802L,
    0x04200002L,
    0x04200002L,
    2L,
    0x00200002L,
    0x04000000L,
    0x04000800L,
    2097152L,
    0x04200800L,
    0x00000802L,
    0x00200802L,
    0x04200800L,
    0x00000802L,
    0x04000002L,
    0x04200802L,
    0x04200000L,
    0x00200800L,
    0x00000000L,
    2L,
    0x04200802L,
    0x00000000L,
    0x00200802L,
    0x04200000L,
    2048L,
    0x04000002L,
    0x04000800L,
    2048L,
    0x00200002L,
    ]

SP8 = [
    0x10001040L,
    4096L,
    262144L,
    0x10041040L,
    0x10000000L,
    0x10001040L,
    64L,
    0x10000000L,
    0x00040040L,
    0x10040000L,
    0x10041040L,
    0x00041000L,
    0x10041000L,
    0x00041040L,
    4096L,
    64L,
    0x10040000L,
    0x10000040L,
    0x10001000L,
    0x00001040L,
    0x00041000L,
    0x00040040L,
    0x10040040L,
    0x10041000L,
    0x00001040L,
    0x00000000L,
    0x00000000L,
    0x10040040L,
    0x10000040L,
    0x10001000L,
    0x00041040L,
    262144L,
    0x00041040L,
    262144L,
    0x10041000L,
    4096L,
    64L,
    0x10040040L,
    4096L,
    0x00041040L,
    0x10001000L,
    64L,
    0x10000040L,
    0x10040000L,
    0x10040040L,
    0x10000000L,
    262144L,
    0x10001040L,
    0x00000000L,
    0x10041040L,
    0x00040040L,
    0x10000040L,
    0x10040000L,
    0x10001000L,
    0x10001040L,
    0x00000000L,
    0x10041040L,
    0x00041000L,
    0x00041000L,
    0x00001040L,
    0x00001040L,
    0x00040040L,
    0x10000000L,
    0x10041000L,
    ]


def desfunc(block, keys):
    (leftt, right) = unpack('>II', block)

    work = (leftt >> 04 ^ right) & 0x0f0f0f0fL
    right ^= work
    leftt ^= work << 04
    work = (leftt >> 020 ^ right) & 0x0000ffffL
    right ^= work
    leftt ^= work << 020
    work = (right >> 02 ^ leftt) & 0x33333333L
    leftt ^= work
    right ^= work << 02
    work = (right >> 010 ^ leftt) & 0x00ff00ffL
    leftt ^= work
    right ^= work << 010
    right = (right << 01 | right >> 31 & 1L) & 0xffffffffL
    work = (leftt ^ right) & 0xaaaaaaaaL
    leftt ^= work
    right ^= work
    leftt = (leftt << 01 | leftt >> 31 & 1L) & 0xffffffffL

    for i in range(0, 040, 04):
        work = right << 28 | right >> 04
        work ^= keys[i]
        fval = SP7[work & 63L]
        fval |= SP5[work >> 010 & 63L]
        fval |= SP3[work >> 020 & 63L]
        fval |= SP1[work >> 24 & 63L]
        work = right ^ keys[i + 01]
        fval |= SP8[work & 63L]
        fval |= SP6[work >> 010 & 63L]
        fval |= SP4[work >> 020 & 63L]
        fval |= SP2[work >> 24 & 63L]
        leftt ^= fval
        work = leftt << 28 | leftt >> 04
        work ^= keys[i + 02]
        fval = SP7[work & 63L]
        fval |= SP5[work >> 010 & 63L]
        fval |= SP3[work >> 020 & 63L]
        fval |= SP1[work >> 24 & 63L]
        work = leftt ^ keys[i + 3]
        fval |= SP8[work & 63L]
        fval |= SP6[work >> 010 & 63L]
        fval |= SP4[work >> 020 & 63L]
        fval |= SP2[work >> 24 & 63L]
        right ^= fval

    right = right << 31 | right >> 01
    work = (leftt ^ right) & 0xaaaaaaaaL
    leftt ^= work
    right ^= work
    leftt = leftt << 31 | leftt >> 01
    work = (leftt >> 010 ^ right) & 0x00ff00ffL
    right ^= work
    leftt ^= work << 010
    work = (leftt >> 02 ^ right) & 0x33333333L
    right ^= work
    leftt ^= work << 02
    work = (right >> 020 ^ leftt) & 0x0000ffffL
    leftt ^= work
    right ^= work << 020
    work = (right >> 04 ^ leftt) & 0x0f0f0f0fL
    leftt ^= work
    right ^= work << 04

    leftt &= 0xffffffffL
    right &= 0xffffffffL
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
    07,
    ]


def decrypt_passwd(data):
    dk = deskey(pack('8B', *fixedkey), True)
    return desfunc(data, dk)


def generate_response(passwd, challenge):
    ek = deskey((passwd + '\x00' * 010)[:010], False)
    return desfunc(challenge[:010], ek) + desfunc(challenge[010:], ek)


def decrypt_response(passwd, encryptedChallenge):
    dk = deskey((passwd + '\x00' * 010)[:010], True)
    return desfunc(encryptedChallenge[:010], dk) \
        + desfunc(encryptedChallenge[010:], dk)


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
    print 'test succeeded.'
