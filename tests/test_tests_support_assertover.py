import unittest

from tests.support import AssertOver
from tests.support.assertover import NoBlockError, NoCasesError


def assert_a_thing(value):
    assert value.endswith(' thing'), "must end with a thing"


class TestsSupportAssertOver(unittest.TestCase):
    def test_none_failing(self):
        saw_raise = False
        try:
            with AssertOver(values=('some thing', 'other thing')) as value_block:
                value_block(lambda _: assert_a_thing(_))
        except Exception as exc:
            saw_raise = True
        self.assertFalse(saw_raise)

    def test_three_total_two_failing(self):
        with self.assertRaises(AssertionError) as raised:
            with AssertOver(values=('some thing', 'other stuff', 'foobar')) as value_block:
                value_block(lambda _: assert_a_thing(_))

        theexception = raised.exception
        self.assertEqual(str(theexception), """assertions raised for the following values:
- <'other stuff'> : must end with a thing
- <'foobar'> : must end with a thing""")

    def test_no_cases(self):
        with self.assertRaises(AssertionError) as raised:
            with AssertOver(values=()) as value_block:
                value_block(lambda _: assert_a_thing(_))

        theexception = raised.exception
        self.assertIsInstance(theexception, NoCasesError)


if __name__ == '__main__':
    unittest.main()
