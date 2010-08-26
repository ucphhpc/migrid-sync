"""
Exceptions file
"""

class GRSException(Exception): 
    """
    General exception for GRSfs. 
    """
    pass
    
class GRSReplicaOutOfStep(GRSException):
    pass
    
class GRSConfigurationException(GRSException):
    """
    Raised when internal validation of configuration fails
    """
    pass