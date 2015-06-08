#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rfb - An implementation of the RFB Protocol messages.
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

#
# Simon Andreas Frimann Lund
#
# An implementation of the RFB Protocol messages.
# RFB: http://www.realvnc.com/docs/rfbproto.pdf
#
# version / major / minor - Simply "configure" the protocol version.
#                           This implementation is 3.8 only! Not backward compatible.
#
# In addition to the messages described in the standard a couple of additional
# datastructures are available for convenience:
#
# Client struct - Data describing the client (rfb version and data from client init.)
# Server struct - Data describing the server (rfb version and data from server init)
#
# The "struct" module is heavily used to create messages for the network layer
# in an efficient way.
#
# RFB 6 describes the types used, below is a mapping of the types described in
# the standard and the formatting values for the struct.pack function.
#
# Unsigned: u8, u16, u32 = B, H, I
# Signed:   s8, s16, s32 = b, h, i
# Byte-order: big-endian / network order = !
#
# An optimization could be to skip all the static calls to pack, having defined
# all the static protocols messages as simple strings.
# This would reduce readability for people with untrained eyes for hex.
#
# This struct module is a blessing!
#
# -- END_HEADER ---
#

from struct import *

PIXEL_FORMAT = pack('!BBBBHHHBBBBBB', 32, 24, 0, 1, 255, 255, 255, 16, 8, 0, 0, 0, 0)

# Message types as described in 6.4

# RFB 6.2
security = {
  'INVALID'   : pack('!B', 0),
  'NONE'      : pack('!B', 1),
  'VNC_AUTH'  : pack('!B', 2),
  'RA2'       : pack('!B', 5),
  'RA2NE'     : pack('!B', 6),
  'TIGHT'     : pack('!B', 16),
  'ULTRA'     : pack('!B', 17),
  'TLS'       : pack('!B', 18),
  'VENCRYPT'  : pack('!B', 19)
}

# RFB 6.4
clientMessages = {
  'SET_PIXEL_FORMAT'  : pack('!B', 0),
  'SET_ENCODINGS'     : pack('!B', 2),
  'KEY_EVENT'         : pack('!B', 4),
  'POINTER_EVENT'     : pack('!B', 5),
  'CLIENT_CUT_TEXT'   : pack('!B', 6),
  'FRAMEBUFFER_UPDATE_REQUEST' : pack('!B', 3),
  
  # The registrered / non-standard messagetypes are the same for both client and server
  'VMWARE1' : pack('!B', 254),
  'VMWARE2' : pack('!B', 127),
  'GII'     : pack('!B', 253),
  'ANTHONY_LIGUORI' : pack('!B', 255)
}

# RFB 6.5
serverMessages = {
  'BELL'                    : pack('!B', 2),
  'SERVER_CUT_TEXT'         : pack('!B', 3),
  'FRAMEBUFFER_UPDATE'      : pack('!B', 0),
  'SET_COLOUR_MAP_ENTRIES'  : pack('!B', 1),
  
  # The registrered / non-standard messagetypes are the same for both client and server
  'VMWARE1' : pack('!B', 254),
  'VMWARE2' : pack('!B', 127),
  'GII'     : pack('!B', 253),
  'ANTHONY_LIGUORI' : pack('!B', 255)
}

# RFB 6.6
encodings = {
  'RAW'           : pack('!i', 0),
  'COPY_RECT'     : pack('!i', 1),
  'RRE'           : pack('!i', 2),
  'HEXTILE'       : pack('!i', 5),
  'ZRLE'          : pack('!i', 16),
  'CURSOR'        : pack('!i', -239),
  'DESKTOP_SIZE'  : pack('!i', -223)
}

# A bunch of registrered / non-standard encodings exist. See RFB 6.6 for details.

# Experimenting with representing rectangle like this.
# Is this overdoing it?
class Rectangle:
  def __init__(self, x, y, width, height, pixelData):
    self.x = x
    self.y = y
    self.width = width
    self.height = height
    self.pixelData = pixelData
    
## Information based on client init should be stored in this thing
#class ClientInformation():
#  
#  protocolVersion   = None
#  sharedFlag        = False # size?
#  securityType      = None  # size?
#  challengeResponse = None  # size?
#
## Information based on server init should be stored in this thing
#class ServerInformation():
#  
#  protocolVersion   = None  # size?
#  securityTypes     = []    # byte aray would be nice
#  challenge         = None  # size?

# intoN,
#
# Helper function to split a string into a list element each n wide.
# Useful for creating input for struct.pack.
#
# example:
# intoN('hello there', 1)->[int('h'), int('e'), ... , int('e')]
#
def intoN(sequence, n, base=10):
  return (int(sequence[i:i+n], base) for i in range(0, len(sequence), n))

# Protocol version,
#
# The first message in the handshake, send by both client and server, 
def protocolVersion():  
  return "RFB 003.008\n"

# Invalid version,
# 
# Send by the server when the client version is not supported.
#
# RFB 6.1.2
def invalidVersion(reason="VNC Server disconnected because it's got the flue!"):
  return  pack('!B', 0) + \
          pack('!I', len(reason)) + \
          reason;

# Security types,
#
# Server announces supported security types.
#
# RFB 6.1.2
# TODO: improve on this! The available security types are bound.
def securityTypes():
  return pack('!BB', 1, 2)
  #return pack('!BB', 1, 1)

# Security type,
#
# RFB 6.1.2
#
# Client sends the chosen security type to server.
# Response to securityTypes
def securityType(type):
  return pack('!B', type)

# Security result success,
#
# RFB 6.1.3
# @param success Boolean
def securityResult(succes):
  
  # True == 1 in Python
  # BUT!!
  # True == 0 in RFB
  # Be aware that in RFB 6.3.1 things are more python-ish
  
  # Hence the negation of the boolean
  return pack('!I', int(not succes))

# VNC Authentification challenge
#
# Generate a random 16-byte challenge.
#
# RFB 6.2.2
# TODO: - a static challenge is provided, randomize the "normal" version
def vncAuthChallenge():
  return pack('!16B', *intoN('29c2a0229ac73a43751a248a975d469d', 2, 16))
  
def vncStaticAuthChallenge():
  return pack('!16B', *intoN('29c2a0229ac73a43751a248a975d469d', 2, 16))

# VNC Authentification response
#
# Encrypt challenge with DES using a password supplied by the user as the
# key and send the resulting 16-byte response.
#
# RFB 6.2.2
def vncAuthResponse(response):
  if len(response) != 16:
    raise NameError
  return response

# Initialization

# Client Initialization
#
# Shared-flag is non-zero (true) if the server should try to share the desktop
# by leaving other clients connected, zero (false) if it should give exclusive
# access to this client by disconnecting all other clients.
#
# RFB 6.3.1
def clientInit(sharedDesktop):
  return pack('!I', int(sharedDesktop))
  
# Server Initialization

# TODO: Pixel format
def serverInit(width, height, format, name):
  return  pack('!HH', width, height) +\
          format +\
          pack('!I', len(name)) +\
          name

# Client to server messages

# TODO: Figure out what's wrong here... according to the standard then the message
#       below needs padding before and after. But according to reverse engineering
#       of x11vnc then that's not the case!
#
# RFB 6.4.1
def setPixelFormat(bpp, depth, bigEndian, trueColor,
                   redMax, greenMax, blueMax,
                   redShift, greenShift, blueShift):
  
  return pack('!BBBBBHHHBBBBBB', 0, bpp, depth, int(bigEndian), int(trueColor),
              redMax, greenMax, blueMax,
              redShift, greenShift, blueShift, 0, 0, 0)

# RFB 6.4.2
#
# TODO: Do something sensible the encodings are specifics.
def setEncodings(encodings=[0, -240, -239, -232]):
  encString = ''
  for enc in encodings:
    encString += pack('!i', enc)
  return pack('!BBH', 2, 0, len(encodings)) +\
          encString

# Framebuffer update request
#
# RFB 6.4.3
#
# @param incremental Boolean
# @param x int
# @param y int
# @param width int
# @param height int
# @return string
def framebufferUpdateRequest(incremental, x, y, width, height):
  return pack("!BBHHHH", 3, int(incremental), x, y, width, height)

# Key event
#
# RFB 6.4.4
def keyEvent(down, key):
  return pack('!BBBB', 4, int(down), 0, 0) + key

# Pointer Event
#
# RFB 6.4.5
def pointerEvent(button, x, y):
  return pack('!BBHH', 5, button, x, y)

# Client cut text
#
# RFB 6.4.6
def clientCutText(text):
  lengthFormat = "!%dB" % len(text)
  return pack('!BBBBI', 6, 0, 0, 0, len(text)) +\
          pack(lengthFormat, *intoN(text,1))

# Server to client messages

# Framebuffer Update
#
# TODO: Add a short description, capturing the essentials. 2-3 lines.
#
# RFB 6.5.1
# TODO: Implement support for other encodings.
# @param rectangles list of class rectangle
def framebufferUpdate(rectangles):
  
  return pack("!BBH", 0, 0, len(rectangles)) +\
        (pack('!HHHHi', r.x, r.y, r.width, r.height, 'RAW', r.pixelData) for r in rectangles)

# Set colour map entries
#
# When the pixel format uses a “colour map”, this message tells the client that
# the specified pixel values should be mapped to the given RGB intensities.
#
# RFB 6.5.2
# TODO: implement
def setColourMapEntries():
  return "NOT IMPLEMENTED"

# Bell
#
# Ring a bell on the client if it has one.
#
# RFB 6.5.3
def bell():
  return pack('!B', 2)

# Server cut text
#
# RFB 6.5.4
def serverCutText(text):
  return pack('!BBBBI', 3, 0, 0, 0, len(text)) + text
