import httplib
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_infrastructure', 'bin']))  # noqa
# common packages
import em_declare  # noqa
from em_rest_aws_impl import EMAwsInterfaceImpl
from rest_handler import rest_interface_splunkd
from rest_handler.rest_interface_splunkd import route
from rest_handler.session import session


class EMAwsInterface(rest_interface_splunkd.BaseRestInterfaceSplunkd):

    logger_name = 'rest_aws'

    @route('/check_env', methods=['GET'])
    def handle_check_env(self, request):
        interface_impl = EMAwsInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered AWS check env')
            response = interface_impl.handle_check_env(request)
            return httplib.OK, response
