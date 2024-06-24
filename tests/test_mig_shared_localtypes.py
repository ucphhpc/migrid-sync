# -*- coding: utf-8 -*-

from tests.support import MigTestCase, testmain

from mig.shared.localtypes import AsciiEnum

DUMMY_UNICODE = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'


class MigSharedLocaltypes__AsciiEnum(MigTestCase):
    def test_defines_the_number_of_cases_specified(self):
        class TheEnum(AsciiEnum):
            SomeCase = 'some case'
            OtherCase = 'other case'
            ZzzCase = 'all the zzz'

        self.assertEqual(len(TheEnum), 3)

    def test_defines_cases_that_behave_as_strings(self):
        class TheEnum(AsciiEnum):
            SomeCase = 'some case'
            OtherCase = 'other case'

        self.assertEqual(TheEnum.SomeCase, 'some case')
        self.assertEqual(TheEnum.OtherCase, 'other case')

    def test_disallows_unicode_keys(self):
        with self.assertRaises(Exception) as cm:
            class TheEnum(AsciiEnum):
                SomeCase = DUMMY_UNICODE

        theexception = cm.exception

        self.assertEqual(theexception.__str__(),
                         u"'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®' is not pure ascii")


if __name__ == '__main__':
    testmain()
