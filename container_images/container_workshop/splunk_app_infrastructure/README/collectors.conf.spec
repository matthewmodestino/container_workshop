[<collector name>]
title = <string>
* The title of the collector.

source_predicate = <string>
* Predicate to discover entities from the metrics index.
* Example: cpu.* (entities have at least one metric_name that starts with cpu)

title_dimension = <string>
* Dimension to use as the entity's title.

identifier_dimensions = <list of strings>
* A list of dimensions used to uniquely identify an entity.

informational_dimensions = <"*" or list of strings>
* Informational dimensions used to describe an entity.
* An array of dimensions' names or "*" for everything except identifier dimensions.

blacklisted_dimensions = <list of strings>
* A list of dimensions that are removed during entity discovery.

monitoring_lag = <int>
* Calculate the latest time, in seconds, to run discovery searches because
there may be a delay between when events reach the HEC endpoint and whenn events are indexed.
* Default is 15.

monitoring_calculation_window = <int>
* The search time range. Use this with monitoring_lag to determine
the precise time range.
* Default is 270.

dimension_display_names = <json>
* An array of dimensions with values in a human-readable format in different locations.
* Example: 
[
    "os": {"en-US": "OS", "zh-CN": "操作系统"},
    "os_version": {"en-US": "Version", "zh-CN": "版本"}
]

disabled = <0|1>
* Enable or disable the collector. A value of 1 enables the collector, and a value of 0 disables the collector.

vital_metrics = <json>
* Default metrics panels on the Entity Analysis Workspace page.
* Example: ["cpu.system", "memory.free"]

correlated_event_data = <json>
* Correlation rules that are used to construct event log filter of an entity to find related log events.
* Example:
'unix_logs': {
    # base search is used as a first pass filer to find events
    # correlated to this collector -- eg. sourcetype=syslog
    'base_search': {
        # a *Boolean filter*, takes a boolean operator and a list of filters
        # (matching BooleanFilter class in em_correlation_filters)
        'type': 'or',
        'filters': [
            {
                # a *Basic filter*, takes a type, field and values
                # (matching BasicFilter class in em_correlation_filters)
                'type': 'include',
                'field': 'sourcetype',
                'values': ['*']
            }
        ]
    },
    # Entity filters are used to correlate between metrics and logs
    # by searching for logs whose value of event_field is the value of dimension_name
    # in metrics data -- eg. host=alabama.usa.com
    'entity_filters': {
        'type': 'or',
        'filters': [
            {
                # an *Entity filter*, takes a event_field and dimension_name
                # (matching EntityFilter class in em_correlation_filters)
                'event_field': 'host',
                'dimension_name': 'host'
            }
        ]
    }
}

