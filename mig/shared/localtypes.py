from enum import ReprEnum
from past.builtins import basestring

""" A module containing a set of commonly used local data strutures.

The use of no internal dependencies ensures the provided primitives
can be used as the basis for defining any other parts of the system.
"""


def _isascii(value):
    """Given a string establish that is conatains only plain ascii.
    """
    assert isinstance(value, basestring)
    return not any((b > 0x7f for b in bytearray(value, 'utf8')))


class AsciiEnum(str, ReprEnum):
    """
    Enum where members behave as strings and are reuired to contain only ascii.
    """

    def __new__(cls, *values):
        if len(values) != 1:
            raise TypeError(
                'only a single argument is supported: %r' % (values, ))
        thestring = str(values[0])
        if not isinstance(thestring, basestring):
            raise TypeError('%r is not a string' % (thestring, ))
        if not _isascii(thestring):
            raise TypeError('%r is not pure ascii' % (thestring, ))
        member = str.__new__(cls, thestring)
        member._value_ = thestring
        return member
