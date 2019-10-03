import em_declare  # noqa
import requests
from em_constants import AWS_ENV_CHECK_URL, DEPLOYMENT_EC2, DEPLOYMENT_NON_EC2

# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext


class EMAwsInterfaceImpl(object):

    def __init__(self, session_key, logger):
        self.session_key = session_key
        self.logger = logger

    def handle_check_env(self, request):
        """
        Check if environment is running on EC2 or not
        """
        response = {
            'deployment': {}
        }
        try:
            requests.get(AWS_ENV_CHECK_URL, timeout=2)
            deployment_env = DEPLOYMENT_EC2
        except IOError:
            self.logger.error('Not running on EC2 instance')
            deployment_env = DEPLOYMENT_NON_EC2

        response['deployment']['env'] = deployment_env
        return response
