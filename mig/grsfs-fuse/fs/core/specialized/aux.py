#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# aux - [insert a few words of module description on this line]
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""
Contains stuff that didn't fit anywhere else

Created by Jan Wiberg on 2010-03-22.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import os, syslog, itertools

def flag2mode(flags):
    """
        Takes a set of os.O_x flags and creates a python 
        'open'-compatible string
    """
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    mode = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        mode = mode.replace('w', 'a', 1)

    return mode
    
    
# some notes for later:

# def synchronized_iterator(f):
#     def wrapper(*args,**kwargs):
#         class iterator(object):
#             def __init__(self,f,args,kwargs):
#                 self.iter = f(*args,**kwargs)
#                 self.lock = threading.RLock()
#             def __iter__(self):
#                 return self
#             def next(self):
#                 self.lock.acquire()
#                 try:
#                     return self.iter.next()
#                 finally:
#                     self.lock.release()
#         return iterator(f,args,kwargs)
#     return wrapper
# 
# @synchronized_iterator
# def create_counter():
#     t = itertools.count()
#     while True:
#         yield t.next()
# 
# or
# 
# counter = synchronized_iterator(itertools.count)

## {{{ http://code.activestate.com/recipes/576529/ (r5)
# By Christian Muirhead, Menno Smits and Michael Foord 2008
# WTF license
# http://voidspace.org.uk/blog


# this next part is a dynamic trick for filling in rich comparators (c) http://code.activestate.com/recipes/576529/
import sys as _sys

if _sys.version_info[0] == 3:
    def _has_method(cls, name):
        for B in cls.__mro__:
            if B is object:
                continue
            if name in B.__dict__:
                return True
        return False
else:
    def _has_method(cls, name):
        for B in cls.mro():
            if B is object:
                continue
            if name in B.__dict__:
                return True
        return False



def _ordering(cls, overwrite):
    def setter(name, value):
        if overwrite or not _has_method(cls, name):
            value.__name__ = name
            setattr(cls, name, value)
            
    comparison = None
    if not _has_method(cls, '__lt__'):
        for name in 'gt le ge'.split():
            if not _has_method(cls, '__' + name + '__'):
                continue
            comparison = getattr(cls, '__' + name + '__')
            if name.endswith('e'):
                eq = lambda s, o: comparison(s, o) and comparison(o, s)
            else:
                eq = lambda s, o: not comparison(s, o) and not comparison(o, s)
            ne = lambda s, o: not eq(s, o)
            if name.startswith('l'):
                setter('__lt__', lambda s, o: comparison(s, o) and ne(s, o))
            else:
                setter('__lt__', lambda s, o: comparison(o, s) and ne(s, o))
            break
        assert comparison is not None, 'must have at least one of ge, gt, le, lt'

    setter('__ne__', lambda s, o: s < o or o < s)
    setter('__eq__', lambda s, o: not s != o)
    setter('__gt__', lambda s, o: o < s)
    setter('__ge__', lambda s, o: not (s < o))
    setter('__le__', lambda s, o: not (s > o))
    return cls


def total_ordering(cls):
    return _ordering(cls, False)

def force_total_ordering(cls):
    return _ordering(cls, True)

def decorator_with_args(decorator):
    def new(*args, **kwargs):
        def new2(fn):
            return decorator(fn, *args, **kwargs)
        return new2
    return new

@decorator_with_args
def typecheck(fn, *decorator_args):
    def new(*args):
        if len(decorator_args) != len(args):
            raise Exception('Wrong number of arguments given to\
                             decorator.')
        for x in range(0, len(args)):
            if type(args[x]) != decorator_args[x]:
                raise TypeError('Argument %i is of wrong type.\
                                 %s expected, %s received.'%\
                               (x+1, str(decorator_args[x]),
                                str(type(args[x]))))
        return fn(*args)
    return new
    
    
## {{{ http://code.activestate.com/recipes/465057/ (r1)
def synchronized(lock):
    """ Synchronization decorator. """

    def wrap(f):
        def newFunction(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return newFunction
    return wrap

