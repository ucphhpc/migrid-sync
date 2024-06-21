from past.builtins import basestring
from enum import ReprEnum
from types import SimpleNamespace

""" A module containing a set of commonly used local data strutures.

The use of no internal dependencies ensures the provided primitives
can be used as the basis for defining any other parts of the system.
"""


def _isascii(s):
    """Given a string establish that is conatains only plain ascii.
    """
    assert isinstance(s, basestring)
    return not any((b > 0x7f for b in bytearray(s, 'utf8')))


class AsciiEnum(str, ReprEnum):
    """
    Enum where members behave as strings and are reuired to contain only ascii.
    """

    def __new__(cls, *values):
        "values must already be of type `str`"
        if len(values) != 1:
            raise TypeError(
                'only a single argument is supported: %r' % (values, ))
        thestring = values[0]
        if not isinstance(thestring, str):
            raise TypeError('%r is not a string' % (thestring, ))
        if not _isascii(thestring):
            raise TypeError('%r is not pure ascii' % (thestring, ))
        member = str.__new__(cls, thestring)
        member._value_ = thestring
        return member


def namedconstants(name, d):
    """Given a closed set of key-value pairs sepcified by a dict define
    an immutable object which exposes these mappings via subscripting.
    """

    class _Constants(SimpleNamespace):
        __slots__ = [k.name for k in d.keys()]

        def __init__(self, defaults):
            super(_Constants, self).__init__(**defaults)

        def __getitem__(self, key):
            return self.__getattribute__(key)
    return _Constants(d)
