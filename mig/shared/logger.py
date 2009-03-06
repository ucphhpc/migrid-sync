#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# logger - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Logger class"""

import logging


class Logger:
    """ MiG code should use an instance of this class to handle
    writing to log-files.
    """
    
    logger = None
    logginglevel = None
    hdlr = None
    logfile = None
    logginglevel = None
    
    def __init__(self, logfile, level):
        self.logfile = logfile
        self.logger = logging.getLogger('mig_main_logger')
        # Repeated import of Configuration in cgi's would cause echo
        # in log files if a second handler is added to the existing
        # logger!
        if not self.logger.handlers:
            self.init_handler()
        else:
            self.hdlr = self.logger.handlers[0]
        
        if level == "debug":
            self.logginglevel = logging.DEBUG
        elif level == "info":
            self.logginglevel = logging.INFO
        elif level == "error":
            self.logginglevel = logging.ERROR
        else:
            # default
            print "Unknown logging level %s, using logging.error!" % (level)
            self.logginglevel = logging.error
        self.logger.setLevel(self.logginglevel)

    def init_handler(self, stderr=False):
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
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
        if stderr:
            # Remove stderr handler
            self.logger.removeHandler(self.console)
        else:
            # Remove file handler
            self.logger.removeHandler(self.hdlr)
    
    def loglevel(self):
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
