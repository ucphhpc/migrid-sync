#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# safeeval - Safe evaluation of expressions and commands
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Safe evaluation of user supplied price function expressions and of local
commands with or without shell interpretation.

The safe expression-evaluation is based on example from:
http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/286134

The commands rely on the subprocess functions with shell=False if the command
line arguments may contain user-provided variables with control characters in
them. For the cases where we explicitly sanitize all command line arguments
we can additionally use the version with shell=True.

Please ALWAYS only use the command line calls from this function in server side
code. I.e. NO direct os.system, os.execX, os.spawnX, os.popen, subprocess.X or
`cmd` calls!
Also try hard not to use the shell invocation if at all possible.
"""

import dis
import subprocess
# expose STDOUT and PIPE as vars
subprocess_stdout, subprocess_pipe = subprocess.STDOUT, subprocess.PIPE

_const_codes = map(dis.opmap.__getitem__, [
    'POP_TOP',
    'ROT_TWO',
    'ROT_THREE',
    'ROT_FOUR',
    'DUP_TOP',
    'BUILD_LIST',
    'BUILD_MAP',
    'BUILD_TUPLE',
    'LOAD_CONST',
    'RETURN_VALUE',
    'STORE_SUBSCR',
    ])

_expr_codes = _const_codes + map(dis.opmap.__getitem__, [
    'UNARY_POSITIVE',
    'UNARY_NEGATIVE',
    'UNARY_NOT',
    'UNARY_INVERT',
    'BINARY_POWER',
    'BINARY_MULTIPLY',
    'BINARY_DIVIDE',
    'BINARY_FLOOR_DIVIDE',
    'BINARY_TRUE_DIVIDE',
    'BINARY_MODULO',
    'BINARY_ADD',
    'BINARY_SUBTRACT',
    'BINARY_LSHIFT',
    'BINARY_RSHIFT',
    'BINARY_AND',
    'BINARY_XOR',
    'BINARY_OR',
    ])

# For inclusion of math function
# math.sin(2) requires addition of:
# LOAD_NAME (101), LOAD_ATTR (105) and CALL_FUNCTION (131)

_math_expr_codes = _expr_codes + map(dis.opmap.__getitem__, ['LOAD_NAME'
        , 'LOAD_ATTR', 'CALL_FUNCTION'])

# TODO: add more?
# Keep this list in sync with import list in math_expr_eval
# Please note that the last functions are 'built-in' and *not* from math

_math_names = [
    'sin',
    'cos',
    'exp',
    'ceil',
    'floor',
    'fabs',
    'floor',
    'fmod',
    'log',
    'log10',
    'pi',
    'e',
    'sqrt',
    'abs',
    'sum',
    'round',
    'pow',
    'min',
    'max',
    'cmp',
    ]


def _get_opcodes(codeobj):
    """_get_opcodes(codeobj) -> [opcodes]

    Extract the actual opcodes as a list from a code object
    
    >>> c = compile(\"[1 + 2, (1,2)]\", \"\", \"eval\")
    >>> _get_opcodes(c)
    [100, 100, 23, 100, 100, 102, 103, 83]
    """

    i = 0
    opcodes = []
    s = codeobj.co_code
    while i < len(s):
        code = ord(s[i])
        opcodes.append(code)
        if code >= dis.HAVE_ARGUMENT:
            i += 3
        else:
            i += 1

    return opcodes


# end _get_opcodes

# Added to allow check for math functions


def _get_opnames(codeobj):
    """_get_opnames(codeobj) -> [opnames]

    Extract the actual opnames as a list from a code object
    
    >>> c = compile(\"[1 + 2, (1,2)]\", \"\", \"eval\")
    >>> _get_opnames(c)
    [('math','cos'),('sys','exit')]
    """

    # print "codeobj.co_names", codeobj.co_names

    opnames = []
    s = codeobj.co_names

    for name in s:
        opnames.append(name)

    return opnames


# end _get_opnames

# Modified to include arg checks if allowed_args is supplied


def test_expr(expr, allowed_codes, allowed_args=[]):
    """test_expr(expr) -> codeobj
    
    Test that the expression contains only the listed opcodes.
    If the expression is valid and contains only allowed codes,
    return the compiled code object. Otherwise raise a ValueError
    """

    try:
        c = compile(expr, '', 'eval')
    except:

        # fixed this print to actually insert expr (original contains ',' instead
        # of '%') - Jonas

        raise ValueError, '%s is not a valid expression' % expr
    codes = _get_opcodes(c)
    for code in codes:

        # print "code:", code

        if code not in allowed_codes:
            raise ValueError, 'opcode %s not allowed' % dis.opname[code]

    if allowed_args:
        args = _get_opnames(c)
        for arg in args:

            # print "arg:", arg

            if arg not in allowed_args:
                raise ValueError, 'opname not allowed: ' + str(arg)

    return c


# end test_expr


def const_eval(expr):
    """const_eval(expression) -> value
    
    Safe Python constant evaluation
    
    Evaluates a string that contains an expression describing
    a Python constant. Strings that are not valid Python expressions
    or that contain other code besides the constant raise ValueError.
    
    >>> const_eval(\"10\")
    10
    >>> const_eval(\"[1,2, (3,4), {'foo':'bar'}]\")
    [1, 2, (3, 4), {'foo': 'bar'}]
    >>> const_eval(\"1+2\")
    Traceback (most recent call last):
    ...
    ValueError: opcode BINARY_ADD not allowed
    """

    c = test_expr(expr, _const_codes)
    return eval(c)


def expr_eval(expr):
    """expr_eval(expression) -> value
    
    Safe Python expression evaluation
    
    Evaluates a string that contains an expression that only
    uses Python constants. This can be used to e.g. evaluate
    a numerical expression from an untrusted source.
    
    >>> expr_eval(\"1+2\")
    3
    >>> expr_eval(\"[1,2]*2\")
    [1, 2, 1, 2]
    >>> expr_eval(\"__import__('sys').modules\")
    Traceback (most recent call last):
    ...
    ValueError: opcode LOAD_NAME not allowed
    """

    c = test_expr(expr, _expr_codes)
    return eval(c)


def math_expr_eval(expr):
    """math_expr_eval(math_expression) -> value
    
    Safe Python math expression evaluation
    
    Evaluates a string that contains an expression that only
    uses Python constants and functions from the math module.
    This can be used to e.g. evaluate a mathematical expression
    from an untrusted source.
    
    >>> math_expr_eval(\"1+2\")
    3
    >>> math_expr_eval(\"cos(2)*2\")
    -0.83229367309428481
    >>> math_expr_eval(\"__import__('sys').modules\")
    Traceback (most recent call last):
    ...
    ValueError: opcode LOAD_NAME not allowed
    """

    from math import sin, cos, exp, ceil, floor, fabs, floor, fmod, \
        log, log10, pi, sqrt, e

    c = test_expr(expr, _math_expr_codes, _math_names)
    return eval(c)


def subprocess_check_output(command, stdin=None, stdout=None, stderr=None,
                            env=None, cwd=None,
                            only_sanitized_variables=False):
    """Safe execution of command with output returned as byte string.
    The optional only_sanitized_variables option is used to override the
    default execution without shell interpretation of control characters.
    Please be really careful when using it especially if any parts of your
    command comes from user-provided variables or file names that may contain
    control characters.
    """
    return subprocess.check_output(command, stdin=stdin, env=env, cwd=cwd,
                                   shell=only_sanitized_variables)

def subprocess_call(command, stdin=None, stdout=None, stderr=None, env=None,
                    cwd=None, only_sanitized_variables=False):
    """Safe execution of command.
    The optional only_sanitized_variables option is used to override the
    default execution without shell interpretation of control characters.
    Please be really careful when using it especially if any parts of your
    command comes from user-provided variables or file names that may contain
    control characters.
    """
    return subprocess.call(command, stdin=stdin, stdout=stdout, stderr=stderr,
                           env=env, cwd=cwd, shell=only_sanitized_variables)

def subprocess_popen(command, stdin=None, stdout=None, stderr=None, env=None,
                     cwd=None, only_sanitized_variables=False):
    """Safe execution of command with full process control.
    The optional only_sanitized_variables option is used to override the
    default execution without shell interpretation of control characters.
    Please be really careful when using it especially if any parts of your
    command comes from user-provided variables or file names that may contain
    control characters.
    Returns a subprocess Popen object with wait method, returncode and so on.
    """
    return subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr,
                            env=env, cwd=cwd, shell=only_sanitized_variables)

