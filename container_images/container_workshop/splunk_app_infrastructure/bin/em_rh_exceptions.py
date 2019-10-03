import splunk.admin as admin

import logging_utility

logger = logging_utility.getLogger()


class EmRestException(admin.AdminManagerException):
    """
    Generic exception class for REST/EAI handlers.
    Used to mask exception raised in handler implementaion

    Do NOT use exceptions inheritted from this class in places other than EAI handler
    """
    def __init__(self, message):
        super(EmRestException, self).__init__(message)
        self.message = message
        logger.error(message)


class EmEntityInterfaceInternalException(EmRestException):
    def __init__(self, message):
        super(EmEntityInterfaceInternalException, self).__init__(message)


class EmGroupInterfaceInternalException(EmRestException):
    def __init__(self, message):
        super(EmGroupInterfaceInternalException, self).__init__(message)


class EmAlertInterfaceInternalException(EmRestException):
    def __init__(self, message):
        super(EmAlertInterfaceInternalException, self).__init__(message)


class EmVictorOpsInterfaceInternalException(EmRestException):
    def __init__(self, message):
        super(EmVictorOpsInterfaceInternalException, self).__init__(message)
