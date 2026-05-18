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


class FakeSendEmail:
    """
    Fake for the interception of email sending calls.
    """

    def __init__(self):
        self.calls = []
        self._checked = False

    def __call__(self, *args, **kwargs):
        # Record any arguments upon a call to send email (discarding the
        # leading configuration argument)
        self.calls.append((args, kwargs))
        return True

    def _recipients(self):
        recipients = set()
        for args, kwargs in self.calls:
            email_address = args[0]
            recipients.add(email_address)
        return recipients

    def check_empty_and_reset(self):
        if self._checked:
            # nothing to do
            return

        has_calls = len(self.calls) > 0
        if has_calls:
            surprise_recipients = []
            for args, kwargs in self.calls:
                email_address = args[0]
                surprise_recipients.append(email_address)
            raise AssertionError(
                "detected email sending without expectation: \n  %s"
                % ("\n  ".join(surprise_recipients),)
            )

    def forgive_email(self):
        self._checked = True

    @property
    def called_once(self):
        self._checked = True
        return len(self.calls) == 1

    def email_was_sent_to(self, email_address):
        recipients = self._recipients()
        assert (
            email_address in recipients
        ), "no email was not set to recipient: %s" % (email_address,)
        self._checked = True
        return email_address in recipients


def make_fake_notifier(mig_test_case=None):
    fake_send_email = FakeSendEmail()

    if mig_test_case:
        mig_test_case._register_check(fake_send_email.check_empty_and_reset)

    return SimpleNamespace(send_email=fake_send_email)


def instrument_test_case(mig_test_case=None, mig_configuration=None):
    assert inspect.ismethod(
        getattr(mig_configuration, "context_set", None)
    ), "supplied configuration must be usable at runtime"

    fakes_by_context_key = {
        "notifier": make_fake_notifier(mig_test_case=mig_test_case),
    }
    for content_key, context_value in fakes_by_context_key.items():
        mig_configuration.context_set(content_key, context_value)
