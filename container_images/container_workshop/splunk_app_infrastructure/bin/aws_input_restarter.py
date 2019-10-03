# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
import em_declare  # noqa
# Standard Python Libraries
import sys
import traceback
import json
# Third-Party Libraries
import urllib
import urllib2
import modinput_wrapper.base_modinput
from splunklib import modularinput as smi
from splunklib.client import Service
# Custom Libraries
import em_constants
import em_common
import logging_utility
import logging
from em_utils import get_check_internal_log_message, is_splunk_light

logger = logging_utility.getLogger()


class AWSInputRestarter(modinput_wrapper.base_modinput.SingleInstanceModInput):
    """
    AWS Input Restarter
    This ModInput restarts certain AWS inputs to workaround TA-AWS bugs
    """

    def __init__(self):
        """
        Init modular input
        """
        super(AWSInputRestarter, self).__init__('em', 'aws_input_restarter')
        self.splunkd_messages_service = None
        # set log level to WARNING to make our logging less verbose
        self.set_log_level(logging.WARNING)

    def get_scheme(self):
        """
        Overloaded splunklib modularinput method
        """
        scheme = smi.Scheme('aws_input_restarter')
        scheme.title = ('Splunk Insights for Infrastructure - AWS Input Restarter')
        scheme.description = (
            'Restarts certain AWS inputs to workaround TA-AWS bugs')
        log_level = 'The logging level of the modular input. Defaults to DEBUG'
        scheme.add_argument(smi.Argument('log_level', title='Log Level',
                                         description=log_level,
                                         required_on_create=False))

        return scheme

    def get_app_name(self):
        """
        Overloaded splunklib modularinput method
        """
        return em_constants.APP_NAME

    def validate_input(self, definition):
        """
        Overloaded splunklib modularinput method
        """
        pass

    def collect_events(self, inputs, ew):
        """
        Main loop function, run every "interval" seconds

        This loops picks one CloudWatch input and restarts it

        :return: void
        """
        input_stanza, stanza_args = inputs.inputs.popitem()
        try:
            self.session_key = self._input_definition.metadata['session_key']
            self.splunkd_messages_service = Service(token=self.session_key,
                                                    app=em_constants.APP_NAME,
                                                    owner='nobody').messages
            if not em_common.modular_input_should_run(self.session_key, logger=logger):
                logger.info("Skipping aws_input_restarter modinput execution on non-captain node.")
                return

            request = self.generate_cloudwatch_input_request('GET')

            logger.info('Fetching AWS CloudWatch inputs...')
            response = urllib2.urlopen(request)
            response = json.loads(response.read())

            # If there's an input, disable then enable it
            if not len(response.get('entry', [])):
                logger.info('No AWS CloudWatch inputs found, exiting...')
                return

            input_name = response['entry'][0]['name']
            logger.info('Attempting to restart AWS CloudWatch input: ' + input_name)
            disable_request = self.generate_cloudwatch_input_request(
                'POST',
                data={'disabled': 1},
                name=input_name)

            enable_request = self.generate_cloudwatch_input_request(
                'POST',
                data={'disabled': 0},
                name=input_name)

            logger.info('Disabling AWS CloudWatch input: ' + input_name)
            disable_response = urllib2.urlopen(disable_request)
            disable_response = json.loads(disable_response.read())

            logger.info('Enabling AWS CloudWatch input: ' + input_name)
            enable_response = urllib2.urlopen(enable_request)
            enable_response = json.loads(enable_response.read())

            logger.info('Modular input execution complete!')
        except urllib2.HTTPError as err:
            if err.code == 404:
                logger.warning('AWS TA is not installed. Can not run aws_input_restarter.')
                return
        except:
            error_type, error, tb = sys.exc_info()
            message = 'AWS Input Restarter Modular input execution failed: ' + unicode(error)
            logger.error(message + '\nTraceback:\n' + ''.join(traceback.format_tb(tb)))
            is_light = is_splunk_light(server_uri=em_common.get_server_uri(),
                                       session_key=self.session_key,
                                       app=em_constants.APP_NAME)
            link_to_error = get_check_internal_log_message(is_light)
            self.splunkd_messages_service.create(
                'aws-input-restarter-failure',
                severity='warn',
                value=('Failed to restart AWS data collection inputs.'
                       ' Newly added EC2 instances will cease to be detected. ' + link_to_error)
            )

    def generate_cloudwatch_input_request(self, method, data=None, name=None):
        base_url = '%s/servicesNS/nobody/Splunk_TA_aws/splunk_ta_aws_aws_cloudwatch/%s?%s'
        headers = {
            'Authorization': 'Splunk %s' % self.session_key,
            'Content-Type': 'application/json'
        }

        # Handle the query params that are passed in
        server_uri = em_common.get_server_uri()
        query_params = dict(output_mode='json')
        query_params['count'] = 1
        query_params['offset'] = 0

        # Build the URL and make the request
        url = base_url % (server_uri, name or '', urllib.urlencode(query_params))
        request = urllib2.Request(
            url,
            urllib.urlencode(data) if data else None,
            headers=headers)
        request.get_method = lambda: method

        return request

if __name__ == '__main__':
    exitcode = AWSInputRestarter().run(sys.argv)
    sys.exit(exitcode)
    pass
