import splunk.admin as admin

from em_collector_configuration_interface_impl import EmCollectorConfigurationInterfaceImpl


class EmCollectorConfigurationInterface(admin.MConfigHandler):

    READ_OPTIONAL_PARAMS = ['fields', 'locale']

    def setup(self):
        if self.requestedAction == admin.ACTION_LIST:
            for arg in self.READ_OPTIONAL_PARAMS:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        interface = EmCollectorConfigurationInterfaceImpl()
        interface.handleList(self, confInfo)


admin.init(EmCollectorConfigurationInterface, admin.CONTEXT_APP_ONLY)
