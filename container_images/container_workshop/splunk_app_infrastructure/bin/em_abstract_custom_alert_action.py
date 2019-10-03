import sys
import logging
import em_constants as EMConstants
import json
import splunk.rest as rest
import em_common as EMCommon
from abc import ABCMeta, abstractmethod


class AbstractCustomAlertAction(object):
    """
    Abstract class holds common opetations across alert actions.
    """
    __metaclass__ = ABCMeta

    def process_payload(self, payload):
        """
        Fetches the search results by using the sid from the payload
        """
        sid = payload.get('sid')
        search_name = payload.get('search_name')
        session_key = payload.get('session_key')

        logging.error('INFO custom alert action em_write_alerts triggered, search_name = %s' % search_name)
        endpoint = EMConstants.SEARCH_RESULTS_ENDPOINT % (EMCommon.get_server_uri(), EMConstants.APP_NAME, sid)
        getargs = {'output_mode': 'json', 'count': 0}
        _, content = rest.simpleRequest(endpoint, session_key, method='GET', getargs=getargs)
        return json.loads(content)

    def run(self):
        """
        called in the __main__ block of each the alert action.
        """
        # logging setup
        sh = logging.StreamHandler()
        log = logging.getLogger()
        log.setLevel(logging.INFO)
        log.addHandler(sh)

        # run the script
        if len(sys.argv) > 1 and sys.argv[1] == '--execute':
            try:
                payload = json.loads(sys.stdin.read())
                self.execute_action(payload)
            except Exception as e:
                logging.error(e)
                sys.exit(3)
        else:
            logging.error('FATAL Unsupported execution mode (expected --execute flag)')
            sys.exit(1)

    def execute_action(self, payload):
        """
        Processes the payload and calls the alert specific execute function to perform actions
        on the search results
        """
        content = self.process_payload(payload)
        results = content['results']
        self.execute(results, payload)

    @abstractmethod
    def execute(self, result, payload):
        """
        All child class should override this method to perform custom actions on the results
        """
        raise NotImplemented("Abstract method not implemented")
