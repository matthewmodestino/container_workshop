import httplib
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_infrastructure', 'bin']))  # noqa

import em_declare  # noqa
import rest_handler.rest_interface_splunkd as rest_interface_splunkd
from rest_handler.rest_interface_splunkd import route
from rest_handler.session import session
from em_rest_victorops_impl import EmVictorOpsInterfaceImpl


class EmVictorOpsInterface(rest_interface_splunkd.BaseRestInterfaceSplunkd):

    logger_name = 'rest_victorops'

    @route('/data', methods=['GET', 'POST'])
    def list_or_create_victorops(self, request):
        interface_impl = EmVictorOpsInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('user triggered list victorops')
            vos = interface_impl.handle_list(request)
            return httplib.OK, vos[0].raw() if len(vos) else {}
        else:
            self.logger.info('user triggered create victorops')
            vo = interface_impl.handle_create(request)
            return httplib.CREATED, vo.raw()

    @route('/data/{vo_id}', methods=['GET', 'POST', 'DELETE'])
    def operate_single_vo(self, request, vo_id):
        interface_impl = EmVictorOpsInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('user triggered get victorops')
            vo = interface_impl.handle_get(request, vo_id)
            return httplib.OK, vo.raw()
        elif request.method == 'POST':
            self.logger.info('user triggered update victorops')
            vo = interface_impl.handle_edit(request, vo_id)
            return httplib.OK, vo.raw()
        else:
            self.logger.info('user triggered delete victorops')
            res = interface_impl.handle_remove(request, vo_id)
            if res:
                return httplib.OK, {}
