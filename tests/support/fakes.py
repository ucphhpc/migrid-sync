# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# __init__ - package marker and core package functions
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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

"""Fake implementations of various assistant functionality used by MiG logic."""

import inspect
from types import SimpleNamespace

__INSTRUMENTED_MARKER = "__" + __name__


class FakeSendEmail:
    """
    Fake for the interception of email sending calls.
    """

    def __init__(self):
        self.calls = []
        self._checked = set()
        self._forgive = False
        self._recipients = None

    def __call__(self, *args, **kwargs):
        # Record any arguments upon a call to send email (discarding the
        # leading configuration argument)
        self.calls.append((args, kwargs))
        return True

    def all_recipients(self):
        if self._recipients:
            return self._recipients

        recipients = set()
        for args, kwargs in self.calls:
            email_address = args[0]
            recipients.add(email_address)
        self._recipients = recipients
        return recipients

    def check_empty_and_reset(self):
        if self.is_checked():
            # nothing to do
            return

        suprise_recipients = self.all_recipients() - self._checked
        if not suprise_recipients:
            # all have been checked
            return

        display_recipients = sorted(suprise_recipients)
        raise AssertionError('detected email sending without expectation: \n  %s'
                                % ('\n  '.join(display_recipients),))

    def is_checked(self):
        if self._forgive:
            return True

        has_calls = len(self.calls) > 0
        if not has_calls:
            return True

        return False

    def forgive_email(self):
        self._forgive = True

    @property
    def called_once(self):
        was_called_once = len(self.calls) == 1
        if was_called_once:
            self._forgive = True
        return was_called_once

    def email_was_sent_to(self, email_address):
        recipients = self.all_recipients()

        assert (
            email_address in recipients
        ), "no email was not set to recipient: %s" % (email_address,)

        self._checked.add(email_address)

        return email_address in recipients

    def total_emails_sent(self):
        total = len(self.calls)
        self._forgive = True
        return total


def make_fake_notifier(mig_test_case=None):
    fake_send_email = FakeSendEmail()

    if mig_test_case:
        mig_test_case._register_check(fake_send_email.check_empty_and_reset)

    return SimpleNamespace(send_email=fake_send_email)


def instrument_test_case(mig_test_case=None, mig_configuration=None):
    assert inspect.ismethod(
        getattr(mig_configuration, "context_set", None)
    ), "supplied configuration must be usable at runtime"

    maybe_marker = getattr(mig_configuration, __INSTRUMENTED_MARKER, None)
    if maybe_marker is __INSTRUMENTED_MARKER:
        return

    fakes_by_context_key = {
        "notifier": make_fake_notifier(mig_test_case=mig_test_case),
    }
    for content_key, context_value in fakes_by_context_key.items():
        mig_configuration.context_set(content_key, context_value)

    setattr(mig_configuration, __INSTRUMENTED_MARKER, __INSTRUMENTED_MARKER)
