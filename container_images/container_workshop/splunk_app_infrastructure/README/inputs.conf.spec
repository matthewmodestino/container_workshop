[em_entity_manager://<name>]
# A modular input which is responsible for managing entity includes: discovery new entities, check entity health.
log_level = <DEBUG|INFO|WARN|ERROR>
# The logging level of the modular input.  Defaults to DEBUG

[aws_input_restarter://<name>]
# A modular input which is responsible for restarting AWS CloudWatch inputs to workaround EC2 discovery issues
log_level = <DEBUG|INFO|WARN|ERROR>
# The logging level of the modular input.  Defaults to DEBUG

[em_entity_migration://<name>]
# A modular input which is responsible for migrating entity to message bus URL
log_level = <DEBUG|INFO|WARN|ERROR>
# The logging level of the modular input.  Defaults to DEBUG 
publish_url= <string>
# The publish URL of the message bus, i.e: servicesNS/nobody/SA-ITOA/itoa_entity_exchange/publish
