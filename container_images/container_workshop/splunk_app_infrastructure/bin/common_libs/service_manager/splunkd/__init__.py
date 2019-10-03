import sys
from os import path

lib_dir = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))  # noqa
sys.path.append(lib_dir)  # noqa
from service_manager import BaseServiceManager, BaseServiceManagerException


class SplunkdServiceManagerException(BaseServiceManagerException):
    """
    Base exception class for all Splunkd service manager related exceptions
    """
    def __init__(self, message):
        super(SplunkdServiceManagerException, self).__init__(message)


class BaseSplunkdServiceManager(BaseServiceManager):
    """
    BaseSplunkdServiceManager class
    """
    def __init__(self, session_key, server_uri, app, owner='nobody'):
        self.session_key = session_key
        self.server_uri = server_uri
        self.app = app
        self.owner = owner

    def base_uri(self):
        return '{server_uri}/servicesNS/{owner}/{app}'.format(
            server_uri=self.server_uri,
            owner=self.owner,
            app=self.app
        )
