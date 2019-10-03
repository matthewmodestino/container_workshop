# Copyright 2019 Splunk Inc. All rights reserved.

import logging_utility

logger = logging_utility.getLogger()


class EMGroup(object):
    """
    Group Model.

    Attributes:
        _key: Primary key of group in KVStore.
        _user: Owner of group in KVStore.
        title: Title of group.
        name:  key of group
        filter: group filter
        entities_count: count of entities in group
        active_entities: count of active entities in group
    """

    def __init__(self,
                 _key=None,
                 _user=None,
                 title='',
                 name='',
                 filter='',
                 entities_count=0,
                 active_entities=0,
                 inactive_entities=0):
        """
        Return entity object
        """
        self.title = title
        self.name = name
        # TODO: convert this to dict upon init
        self.filter = filter
        self._key = _key
        self.entities_count = entities_count
        self.active_entities = active_entities
        self.inactive_entities = inactive_entities

    def get_raw_data(self):
        """
        Get raw dict object from this entity
        """
        return dict(
            _key=self._key,
            title=self.title,
            name=self.name,
            filter=self.filter,
            entities_count=self.entities_count,
            active_entities=self.active_entities,
            inactive_entities=self.inactive_entities
        )

    def check_entity_membership(self, entity):
        """
        Check if entity belongs to current group
        :type entity: EMEntity
        :param entity: an entity object
        :return: boolean
        """
        filter_dict = EMGroup.convert_filter_string_to_dictionary(self.filter)
        return EMGroup.check_dims_satisfies_filter(entity.dimensions, filter_dict)

    @staticmethod
    def convert_filter_string_to_dictionary(filter_string, append_key=''):
        """
        Convert the group filter string to
        to be a dict with dimension values as list
        for same dimension name.
        ie: input: 'os=linux,os=centos,location=usa'
            return: {'os': ['linux', 'centos'], 'location': ['usa']}
        :param filter_string
        :param append_key: key to use as prefix of keys in the returned dict.
        :return: dict
        """
        extracted_dimensions = {}
        if filter_string:
            for dimension in filter_string.split(','):
                key, value = dimension.strip().split('=')
                extracted_dimensions.setdefault('%s%s' % (append_key, key), set()).add(value)
        for dim, vals in extracted_dimensions.iteritems():
            extracted_dimensions[dim] = list(vals)
        return extracted_dimensions

    @staticmethod
    def check_dims_satisfies_filter(dims, filter_rule):
        """
        Check if dimensions satisfy filter, meaning if dimensions contains key-value pair that are
        specified by the filter
        :type dims: dict
        :param dims: dimension to check
        :type filter_rule: dict
        :param filter_rule:
        :return: boolean
        """
        for filter_dim_name, filter_dim_val in filter_rule.iteritems():
            filter_dim_val = map(lambda v: str(v).lower(), filter_dim_val)
            dim_vals = dims.get(filter_dim_name)

            if not dim_vals:
                return False
            if not isinstance(dim_vals, list):
                dim_vals = [dim_vals]
            matched = False
            for val in dim_vals:
                val = str(val).lower()
                # check if record value is one of the filter values
                if val in filter_dim_val:
                    matched = True
                    break
                # otherwise check if record value matches any of the fuzzy match values
                fuzzy_matches = filter(lambda v: v.endswith('*'), filter_dim_val)
                if len(fuzzy_matches):
                    matched = any(val.startswith(v[:-1]) for v in fuzzy_matches)
            if not matched:
                return False
        return True
