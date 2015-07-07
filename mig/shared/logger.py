#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# logger - logging helpers
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

"""Logging helpers"""

import logging

_default_level = "info"
_default_format = "%(asctime)s %(levelname)s %(message)s"
_debug_format = "%(asctime)s %(module)s:%(funcName)s:%(lineno)s %(levelname)s %(message)s"

def _name_to_level(name):
    """Translate log level name to internal logging value"""
    levels = {"debug": logging.DEBUG, "info": logging.INFO,
              "warning": logging.WARNING, "error": logging.ERROR,
              "critical": logging.CRITICAL}
    name = name.lower()
    if not name in levels:
        print 'Unknown logging level %s, using %s!' % (name, _default_level)
        name = _default_level
    return levels[name]

def _name_to_format(name):
    formats = {"debug": _debug_format, "info": _default_format, 
              "warning": _default_format, "error": _default_format,
              "critical": _default_format}
    name = name.lower()
    if not name in formats:
        print 'Unknown logging format %s, using %s!' % (name, _default_format)
        name = _default_format
    return formats[name]


class Logger:
    """ MiG code should use an instance of this class to handle
    writing to log-files.
    """
    logger = None
    logginglevel = None
    hdlr = None
    logfile = None
    loggingformat = None

    def __init__(self, logfile, level, app='mig_main_logger'):
        self.logfile = logfile
        self.logger = logging.getLogger(app)

        # Repeated import of Configuration in cgi's would cause echo
        # in log files if a second handler is added to the existing
        # logger!

        self.logginglevel = _name_to_level(level)
        self.loggingformat = _name_to_format(level)

        if not self.logger.handlers:
            self.init_handler()
        else:
            self.hdlr = self.logger.handlers[0]

        self.logger.setLevel(self.logginglevel)

    def init_handler(self, stderr=False):
        """Init handler"""
        formatter = logging.Formatter(self.loggingformat)
        if stderr:

            # Add stderr handler

            self.console = logging.StreamHandler()
            self.console.setFormatter(formatter)
            self.logger.addHandler(self.console)
        else:

            # Add file handler

            self.hdlr = logging.FileHandler(self.logfile)
            self.hdlr.setFormatter(formatter)
            self.logger.addHandler(self.hdlr)

    def remove_handler(self, stderr=False):
        """Remove handler"""
        if stderr:

            # Remove stderr handler

            self.logger.removeHandler(self.console)
        else:

            # Remove file handler

            self.logger.removeHandler(self.hdlr)

    def loglevel(self):
        """Return active log level"""
        return logging.getLevelName(self.logginglevel)

    def hangup(self):
        """Reopen log file handlers to catch log rotation"""

        # We can not allow all handlers to be removed since it causes
        # a race. Thus we temporarily introduce a stderr handler while
        # reloading the file handler.

        self.init_handler(stderr=True)
        self.remove_handler(stderr=False)
        self.init_handler(stderr=False)
        self.remove_handler(stderr=True)

    def shutdown(self):
        """Flush all open files and disable logging to prepare for a
        clean shutdown.
        """

        logging.shutdown()


def daemon_logger(name, path=None, level="INFO", log_format=None):
    """Simple logger for daemons to get separate logging in standard format"""
    log_level = _name_to_level(level)
    if not log_format:
        log_format = _name_to_format(level)
    formatter = logging.Formatter(log_format)
    if path:
        handler = logging.FileHandler(path)
    else:
        handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    # Make sure root logger does not filter us
    logging.getLogger().setLevel(log_level)
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger
