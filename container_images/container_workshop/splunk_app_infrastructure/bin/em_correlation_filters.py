import json
import em_common


class FilterEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


def serialize(cor_filter):
    """
    serialize filter into json string

    :param cor_filter: a correlation filter
    :return: json string
    """
    filter_encoder = FilterEncoder()
    return filter_encoder.encode(cor_filter)


def deserialize(data, **kwargs):
    """
    deserialize data into filter objects

    :param data: str/json: data to be deserialized
    :param kwargs: any additional information that you'd like to be passed along
    :return: a filter object
    """
    params = json.loads(data) if isinstance(data, str) else data
    filter_type = params.get('type')
    if not filter_type:
        entity = kwargs.get('entity')
        return EntityFilter(**params).convert_basic(entity)
    if filter_type in BasicFilter.ALLOWED_FILTER_TYPE:
        return BasicFilter(**params)
    return BooleanFilter(filter_type,
                         map(lambda f: deserialize(f, **kwargs), params.get('filters', [])))


def compress(cor_filter):
    """
    compress the correlation filter tree

    :param cor_filter: a correlation filter
    :return: a compressed correlation filter
    """
    if isinstance(cor_filter, BasicFilter):
        return cor_filter
    elif isinstance(cor_filter, EntityFilter):
        raise ValueError("All EntityFilter should be converted to BasicFilter before running the compression.")
    elif isinstance(cor_filter, BooleanFilter):
        # if empty filter -- deletes it
        if len(cor_filter.filters) == 0:
            return None
        # if there's only 1 filter in boolean filter -- extract it out
        if len(cor_filter.filters) == 1:
            return compress(cor_filter.filters[0])
        else:
            new_filters = []
            # if it's an OR filter -- compress the filters inside first, then combine the basic filters if possible
            if cor_filter.type == BooleanFilter.ALLOWED_BOOL_TYPE[0]:
                compressed_filters = filter(lambda cf: cf is not None,
                                            map(lambda inside_filter: compress(inside_filter), cor_filter.filters))
                field_dict = {}
                for f in compressed_filters:
                    if isinstance(f, BasicFilter):
                        field_dict.setdefault((f.field, f.type), []).extend(f.values)
                    else:
                        new_filters.append(f)
                for field_and_type, values in field_dict.iteritems():
                    field, filter_type = field_and_type
                    new_filters.append(BasicFilter(type=filter_type, field=field, values=values))
            # if it's an AND filter -- compress the filters inside and don't do anything
            elif cor_filter.type == BooleanFilter.ALLOWED_BOOL_TYPE[1]:
                new_filters = filter(lambda cf: cf is not None,
                                     map(lambda inside_filter: compress(inside_filter), cor_filter.filters))
            # unwrap boolean filter if filters inside is only 1 item
            if len(new_filters) == 1:
                return new_filters[0]
            return BooleanFilter(bool_type=cor_filter.type, filters=new_filters)
    else:
        raise ValueError("Uknown filter type: \'%s\'" % type(cor_filter))


class BasicFilter(object):
    ALLOWED_FILTER_TYPE = ('include', 'exclude')

    def __init__(self, type='include', field=None, values=None):
        """
        initializes a BasicFilter,
        represents <field>=<values> in SPL (if type is 'include')
        :param type: string, one of 'include' or 'exclude'
        :param field: string, represents the field in logs data
        :param values: string or list, represents the list of values that matches the field
        """
        if type not in BasicFilter.ALLOWED_FILTER_TYPE:
            raise ValueError('Filter type \'%s\' is not in supported list: %s' % (type,
                                                                                  BasicFilter.ALLOWED_FILTER_TYPE))
        self.type = type
        self.field = field
        self.values = values if isinstance(values, list) else [values]

    def __eq__(self, other):
        return isinstance(self, BasicFilter) and \
               self.type == other.type and \
               self.field == other.field and \
               set(self.values) == set(other.values)


class BooleanFilter(object):
    ALLOWED_BOOL_TYPE = ('or', 'and')

    def __init__(self, bool_type, filters=None):
        """
        initializes a BooleanFilter,
        serves as construction tool to build complex representation of SPL queries
        with BasicFilter or other BooleanFilter objects.
        -- eg. sourcetype=syslog AND source=/var/log/messages OR user=admin
        :param bool_type: string, one of 'or' or 'and'
        :param filters: list, allowed types include BasicFilter and BooleanFilter
        """
        if bool_type not in BooleanFilter.ALLOWED_BOOL_TYPE:
            raise ValueError('Filter type \'%s\' is not in supported list: %s' % (bool_type,
                                                                                  BooleanFilter.ALLOWED_BOOL_TYPE))
        self.type = bool_type
        self.filters = [] if filters is None else filters

    def add_filter(self, f):
        if not isinstance(f, BooleanFilter) and not isinstance(f, BasicFilter):
            raise ValueError('Argument of type %s is not supported.' % f.__class__)
        self.filters.append(f)

    def __eq__(self, other):
        return isinstance(other, BooleanFilter) and \
               self.type == other.type and \
               len(self.filters) == len(other.filters) and \
               reduce(lambda a, b: a and b,
                      map(lambda i: self.filters[i] == other.filters[i], xrange(len(self.filters))))


class EntityFilter(object):
    ALLOWED_MATCH_CRITERIA = ('exact', 'partial')

    def __init__(self,
                 event_field=None,
                 dimension_name=None,
                 match_criteria='exact',
                 char_replacement_rules=None):
        """
        initializes an EntityFilter,
        used to find logs data whose <event_field> matches the value of <dimension_name> from metrics data
        -- eg. host=california.usa.com
        :param event_field: string
        :param dimension_name: string
        :param match_criteria: string one of 'partial' or 'exact' (default)
        :param char_replacement_rules: list an array of arrays where each sub-array
               contain two elements [<old_string>, <new_string>]
        """
        if match_criteria not in EntityFilter.ALLOWED_MATCH_CRITERIA:
            raise ValueError('Match criteria \'%s\' is not in supported list: %s'
                             % (match_criteria,
                                EntityFilter.ALLOWED_MATCH_CRITERIA))
        self.event_field = event_field
        self.dimension_name = dimension_name
        self.match_criteria = match_criteria
        self.char_replacement_rules_dict = \
            dict(char_replacement_rules) if char_replacement_rules else {}

    def convert_basic(self, entity):
        """
        convert an EntityFilter to a BasicFilter with the information of the entity
        :param entity: dict, an entity object that carries the value of event_field
        :return: a BasicFilter object
        """
        if not entity:
            raise ValueError('Entity info is missing for entity filter conversion.')
        values = em_common.always_list(entity.get('dimensions', {}).get(self.dimension_name))
        if self.match_criteria == EntityFilter.ALLOWED_MATCH_CRITERIA[1]:
            values = map(lambda v: '*%s*' % v, values)
        if self.char_replacement_rules_dict:
            for old, new in self.char_replacement_rules_dict.iteritems():
                values = map(lambda v: v.replace(old, new), values)
        return BasicFilter(
            type='include',
            field=self.event_field,
            values=values
        )


def create_entity_log_filter(entity, related_collectors):
    """
    create a event data filter given entity information
    and its related collector configurations
    :param entity: dict, with key/values representing attributes of the entity
    :param related_collectors: list, each item is a collector configuration object that discovered this entity
    :return: a BooleanFilter object
    """
    or_collector = BooleanFilter('or')
    for c in related_collectors:
        event_correlators = c.get('correlated_event_data', {})
        or_correlator = BooleanFilter('or')
        for correlator_name, correlator_data in event_correlators.iteritems():
            and_filter = BooleanFilter('and')
            if correlator_data:
                # set up base search
                base_search = correlator_data['base_search']
                base_search_filter = deserialize(base_search)
                and_filter.add_filter(base_search_filter)
                # set up entity filter
                entity_filters_raw = correlator_data['entity_filters']
                entity_filter = deserialize(entity_filters_raw, entity=entity)
                and_filter.add_filter(entity_filter)
            or_correlator.add_filter(and_filter)
        or_collector.add_filter(or_correlator)
    return compress(or_collector)


def create_group_log_filter(collector_entities_match, related_collector):
    """
    create an event data filter given collector and entities information within a group
    :param collector_entities_match: dict: with keys being name of collectors & values being list of entities
    that belongs to the group and are discovered by this collector
    :param related_collector: list: each item being a collector config object related to entities discovered
    in this group
    :return: a Boolean Filter object
    """
    or_collector = BooleanFilter('or')
    for c in related_collector:
        event_correlators = c.get('correlated_event_data', {})
        or_correlator = BooleanFilter('or')
        # loop through correlator to construct filter
        for correlator_name, correlator_data in event_correlators.iteritems():
            if correlator_data:
                and_filter = BooleanFilter('and')
                # set up base search
                base_search = correlator_data['base_search']
                base_search_filter = deserialize(base_search)
                # iterate through entities and construct OR between entity filters
                or_entity = BooleanFilter('or')
                for entity in collector_entities_match.get(c['name'], []):
                    # set up entity filter
                    entity_filters_raw = correlator_data['entity_filters']
                    entity_filter = deserialize(entity_filters_raw, entity=entity)
                    or_entity.add_filter(entity_filter)
                # create AND filter between base search filter and entities filter
                and_filter.add_filter(base_search_filter)
                and_filter.add_filter(or_entity)
                # add filter of this correlator to collector-level OR filter
                or_correlator.add_filter(and_filter)
        # add collector filter to the final OR filter
        or_collector.add_filter(or_correlator)
    return compress(or_collector)
