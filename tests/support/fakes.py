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
import re
from types import SimpleNamespace

# NOTE: we rely on email-validator if available but fall-back to dumb check
try:
    from email_validator import validate_email
except ImportError:
    validate_email = None

__INSTRUMENTED_MARKER = "__" + __name__

TEST_BOGUS_EMAIL = "invalid.user@no-such-mail-domain.org"


def _valid_email_address(address):
    """A simple helper to validate an email address with library or natively"""
    if validate_email is None:
        match = re.match(r'^[A-Za-z0-9+_.]+@[A-Za-z0-9.-]+\.[a-z]+$',
                         address)
        if match:
            _valid = {'email': address}
        else:
            _valid = False
    else:
        try:
            _valid = validate_email(address, check_deliverability=True)
        except Exception:
            # DNS lookup failed
            _valid = False
    if not _valid or _valid['email'] != address:
        return False
    elif address == TEST_BOGUS_EMAIL:
        return False
    return True


class FakeSendEmail:
    """
    Fake for the interception of email sending calls.
    """

    def __init__(self):
        self.calls = []
        self._checked = set()
        self._forgive = False
        self._recipients = None
        self._invalid = None

    def __call__(self, *args, **kwargs):
        # Record any arguments upon a call to send email (discarding the
        # leading configuration argument)
        self.calls.append((args, kwargs))
        # NOTE: fail on invalid address to allow emulating failure in tests
        return _valid_email_address(args[0])

    def invalid_recipients(self):
        """Extract invalid recipient addresses from send email calls"""
        if self._invalid:
            return self._invalid

        invalid = set()
        for args, kwargs in self.calls:
            email_address = args[0]
            if not _valid_email_address(email_address):
                invalid.add(email_address)
        self._invalid = invalid

        return invalid

    def all_recipients(self):
        """Extract recipient addresses from send email calls"""
        if self._recipients:
            return self._recipients

        recipients = set()
        for args, kwargs in self.calls:
            email_address = args[0]
            recipients.add(email_address)
        self._recipients = recipients
        return recipients

    def check_empty_and_reset(self):
        """Verify that only expected send email calls were made - if pending"""
        if self.is_checked():
            # nothing to do
            return

        surprise_recipients = self.all_recipients() - self._checked
        if not surprise_recipients:
            # all have been checked
            return

        display_recipients = sorted(surprise_recipients)
        raise AssertionError(
            "detected email sending without expectation: \n  %s"
            % ("\n  ".join(display_recipients),)
        )

    def is_checked(self):
        """Whether delivery was already checked by tests"""
        if self._forgive:
            return True

        has_calls = len(self.calls) > 0
        if not has_calls:
            return True

        return False

    def forgive_email(self):
        """Silence warnings about unexpected send email calls"""
        self._forgive = True

    def _called_times(self, count):
        """Shared helper to inspect number of send email calls"""
        return len(self.calls) == count

    @property
    def called_once(self):
        """Check if exactly one send email call was made"""
        was_called_once = self._called_times(1)
        if was_called_once:
            self._forgive = True
        return was_called_once

    @property
    def called_twice(self):
        """Check if exactly two send email calls were made"""
        return self._called_times(2)

    def email_was_sent_to(self, email_address):
        """Check if an email was sent to email_address"""
        recipients = self.all_recipients()

        assert (
            email_address in recipients
        ), "no send email call with recipient: %s" % (email_address,)

        self._checked.add(email_address)

        return email_address in recipients

    def email_failed_as_invalid(self, email_address):
        """Check if email_address failed validation when attempted sent"""
        invalid = self.invalid_recipients()
        return email_address in invalid

    def total_emails_sent(self):
        """Count the number of send_email calls made"""
        total = len(self.calls)
        self._forgive = True
        return total


def make_fake_notifier(mig_test_case=None):
    """Instantiate fake email notifier for dev/test centexts."""
    fake_send_email = FakeSendEmail()

    if mig_test_case:
        mig_test_case._register_check(fake_send_email.check_empty_and_reset)

    return SimpleNamespace(send_email=fake_send_email)


def instrument_test_case(mig_test_case=None, mig_configuration=None):
    """Bind instrumentation to a unit test case"""
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
