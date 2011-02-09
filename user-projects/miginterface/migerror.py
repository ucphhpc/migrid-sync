"""
Exceptions raised for errors with Mig inteface.
"""


class MigInterfaceError(Exception):
    def __init__(self, msg, error_code=-1):
        self.msg = msg
        self.error_code = error_code
        
    def __str__(self):
        return self.msg+"\nExit code:"+str(self.error_code)


class MigLocalError(MigInterfaceError):
    pass

class MigServerError(MigInterfaceError):
    pass

class MigUnknownJobIdError(MigServerError):
    pass