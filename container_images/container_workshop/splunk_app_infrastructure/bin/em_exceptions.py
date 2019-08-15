
import logging_utility
import httplib
from rest_handler.exception import BaseRestException

logger = logging_utility.getLogger()


class EmException(Exception):
    """
    General exception class for all internal EM classes
    """
    def __init__(self, message):
        super(EmException, self).__init__(message)
        self.message = message
        logger.error(message)


class VictorOpsCouldNotSendAlertException(EmException):

    def __init__(self, message):
        super(VictorOpsCouldNotSendAlertException, self).__init__(message)


class VictorOpsUsernameAlreadyExistsException(EmException):

    def __init__(self, message):
        super(VictorOpsUsernameAlreadyExistsException, self).__init__(message)


class VictorOpsNotExistException(EmException):

    def __init__(self, message):
        super(VictorOpsNotExistException, self).__init__(message)


class VictorOpsInvalidArgumentsException(EmException):

    def __init__(self, message):
        super(VictorOpsInvalidArgumentsException, self).__init__(message)


class AlertNotFoundException(BaseRestException):

    def __init__(self, message):
        super(AlertNotFoundException, self).__init__(httplib.NOT_FOUND, message)


class AlertInternalException(BaseRestException):

    def __init__(self, message):
        super(AlertInternalException, self).__init__(httplib.INTERNAL_SERVER_ERROR, message)


class AlertArgValidationException(BaseRestException):

    def __init__(self, message):
        super(AlertArgValidationException, self).__init__(httplib.BAD_REQUEST, message)


class AlertAlreadyExistsException(BaseRestException):

    def __init__(self, message):
        super(AlertAlreadyExistsException, self).__init__(httplib.BAD_REQUEST, message)


class AlertActionInvalidArgsException(EmException):

    def __init__(self, message):
        super(AlertActionInvalidArgsException, self).__init__(message)


class ThresholdInvalidArgsException(BaseRestException):

    def __init__(self, message):
        super(ThresholdInvalidArgsException, self).__init__(httplib.BAD_REQUEST, message)


class ArgValidationException(EmException):

    def __init__(self, message):
        super(ArgValidationException, self).__init__(message)


class EntityAlreadyExistsException(EmException):

    def __init__(self, message):
        super(EntityAlreadyExistsException, self).__init__(message)


class EntityInternalException(EmException):

    def __init__(self, message):
        super(EntityInternalException, self).__init__(message)


class EntityNotFoundException(EmException):

    def __init__(self, message):
        super(EntityNotFoundException, self).__init__(message)


class CollectorConfigurationInternalException(EmException):

    def __init__(self, message):
        super(CollectorConfigurationInternalException, self).__init__(message)


class CollectorConfigurationNotFoundException(EmException):

    def __init__(self, message):
        super(CollectorConfigurationNotFoundException, self).__init__(message)
