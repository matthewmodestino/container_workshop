import sys
from os import path

lib_dir = path.dirname(path.dirname(path.abspath(__file__)))  # noqa
sys.path.append(lib_dir)  # noqa
from splunkd_logging.log import SplunkdLogType


class BaseServiceManagerException(Exception):
    """
    Base exception class for all service manager related exceptions
    """
    def __init__(self, message):
        super(BaseServiceManagerException, self).__init__(message)


class BaseServiceManager(object):
    """
    BaseServiceManager class
    """
    __metaclass__ = SplunkdLogType
