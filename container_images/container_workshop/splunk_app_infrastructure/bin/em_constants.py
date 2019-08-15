# Copyright 2016 Splunk Inc. All rights reserved.

from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext


APP_NAME = 'splunk_app_infrastructure'

STORE_COLLECTORS = 'em_collector_configs'
STORE_ENTITIES = 'em_entities'
STORE_GROUPS = 'em_groups'
STORE_THRESHOLDS = 'em_thresholds'
STORE_CLOUD_CONFIGS = 'em_cloud_configs'

INDEX_METRICS = 'em_metrics'
INDEX_EVENTS = 'main'
INDEX_META = 'em_meta'

DEFAULT_BATCH_SIZE = 1000
# Need to change limits.conf to update this value
KVSTORE_SINGLE_FETCH_LIMIT = 50000
ACTIVE = 'active'
INACTIVE = 'inactive'
DISABLED = 'disabled'

NOTIFY_WHEN = {
  'IMPROVE': 'improve',
  'DEGRADE': 'degrade',
  'IMPROVE_OR_DEGRADE': 'improve,degrade',
}

# Migration inputs
ENTITY_MIGRATION_INPUT = "em_entity_migration://job"

# Default publish url for message bus
DEFAULT_PUBLISH_URL = "/servicesNS/nobody/SA-ITOA/itoa_entity_exchange/publish"

# Default metric used for color by in tile view
DEFAULT_METRIC_FOR_COLOR_BY = _('Availability')

# Endpoint to fetch latest created alerts
LATEST_ALERTS_ENDPOINT = '%s/servicesNS/-/%s/admin/alerts/-?%s'

# Endpoint to fetch metadata about created alert
ALERTS_METADATA_ENDPOINT = '%s/servicesNS/-/%s/saved/searches/%s?%s'

# Endpoint to fetch results via search_id
SEARCH_RESULTS_ENDPOINT = '%s/servicesNS/-/%s/search/jobs/%s/results'

# Endpoint to migrate to ITSI
DISABLE_INPUTS_ENDPOINT = \
    "/servicesNS/nobody/%s/configs/conf-inputs/%s/disable"

RELOAD_INPUTS_ENDPOINT = "/servicesNS/nobody/-/configs/inputs/_reload"

# Regular expression to extract alerting entity and alerting metric
ALERTS_SEARCH_EXTRACTION = r'\(?\"(host|InstanceId)\"=\"(?P<alerting_entity>[^\"]+)\"\)? ' \
    'AND metric_name=\"(?P<metric_name>[^\"]+)\"'

# Regular expression to match routing key, from best practices at
# https://help.victorops.com/knowledge-base/routing-keys/
VICTOROPS_ROUTING_KEY = r'^([a-zA-Z0-9\-_])+$'

# Regular expression to match API key.
# (Only contains lower case letters, numbers, and dashes in between)
# I.E - In the form of a GUID/UUID
VICTOROPS_API_KEY = r'^[a-f0-9]{8}-([a-f0-9]{4}-){3}([a-f0-9]{12})$'

# URL from: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html
AWS_ENV_CHECK_URL = 'http://169.254.169.254/latest/meta-data/'

# SII deployment environment types
DEPLOYMENT_EC2 = 'ec2'
DEPLOYMENT_NON_EC2 = 'non-ec2'

# We skip discovery of these dims because including them causes a parse error due to a bug in the mcatalog command.
# SII-3766: added 'status' to this list
DIM_KEYS_BLACKLIST = ['from', 'by', 'where', 'groupby', 'status']

KUBERNETES_COLLECTORS = ['k8s_node', 'k8s_pod']
