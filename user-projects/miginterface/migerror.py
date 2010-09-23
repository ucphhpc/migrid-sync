"""
Exception raised for errors with MiG.
"""
class MigError(Exception):
    """
      Attributes:
                error_type -- the nature of the error
                msg  -- explanation of the error
    """

    def __init__(self, error_type, msg):
        self.type = error_type
        self.msg = msg

    def __str__(self):
        return self.type+"\t"+self.msg
