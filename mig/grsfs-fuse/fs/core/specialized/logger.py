import os
import logging, logging.handlers

class Logger:
    """
    This class (c) pupyMPI group.
    """
    __shared_state = {} # Shared across all instances
    def __init__(self, *args, **kwargs):
        self.__dict__ = self.__shared_state 

        if not "_logger_instance" in self.__dict__:
            self.setup_log(*args, **kwargs)
    """
    parameters:
    quiet: supresses output to console
    debug: Well this parameter is just silly
    verbosity: Set level of incident generating log entries
    """    
    def setup_log(self, logdir, logname, debug, verbosity, quiet):
        if debug or (verbosity > 3):
            verbosity = 3
        
        # Conversion to pythonic logging levels
        verbosity_conversion = [logging.ERROR,logging.WARNING,logging.INFO,logging.DEBUG]        
        level = verbosity_conversion[ verbosity ]
        
        # Decide where to put and what to call the logfile 
        if logdir is not None and os.path.exists(logdir) and os.path.isdir(logdir):
            filepath = logdir + "/" + logname
        
            filelog = logging.FileHandler(filepath)
            #longformatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')
            formatter = logging.Formatter('%(asctime)s %(name)-10s: %(levelname)-7s %(message)s', '%H:%M:%S')
            filelog.setFormatter(formatter)
            filelog.setLevel(level)
            logging.getLogger(logname).addHandler(filelog)
        
        # Add a handler to do std out logging if verbosity demands it and quiet is not on
        if not quiet and verbosity > 0:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            console.setLevel(level)
            logging.getLogger(logname).addHandler(console)

        logger = logging.getLogger(logname)
        logger.setLevel(level)
        self.__dict__['_logger_instance'] = logger
        #self.logger = logger # believed to be superflous

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        if attr not in ("logger", ):
            return setattr(self.logger, attr, value)

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        if attr == "logger":
            return self.__dict__['_logger_instance']
        else: 
            logger = self.__dict__['_logger_instance']
            return getattr(logger, attr)
