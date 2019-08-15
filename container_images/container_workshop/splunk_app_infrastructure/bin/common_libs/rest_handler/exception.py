class BaseRestException(Exception):
    '''
    Base rest exception class whose code and message will be returned as response to
    the user.

    Usage:
    If you would like raise an exception in your custom REST handler class, make sure it
    inherits from BaseRestException. Otherwise "Internal Server Error" will be returned.
    '''

    def __init__(self, code, msg):
        super(BaseRestException, self).__init__(msg)
        self.code = code
        self.msg = msg
