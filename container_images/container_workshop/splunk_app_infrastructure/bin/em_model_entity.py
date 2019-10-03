# Copyright 2016 Splunk Inc. All rights reserved.
# Standard Python Libraries
# Third-Party Libraries
# N/A
# Custom Libraries
import em_common
import logging_utility

logger = logging_utility.getLogger()


class EMEntity(object):
    """
    Entity Model.

    Attributes:
        _key: Primary key of entity in KVStore.
        _user: Owner of entity in KVStore.
        title: Title of entity.
        state: State of entity. Active | Inactive | Disabled
        dimensions: Dictionary representing all key-value pair dimensions.
        identifier_dimensions: List of dimensions to identify this entity
        informational_dimensions: List of dimensions to enhance this entity's information
        imported_date: Time when entity is imported to system.
        updated_date: Last time this entity get updated.
        collectors: list of collectors in the form {name: <string>, updated_date: <number>}
    """

    def __init__(self,
                 _key=None,
                 _user=None,
                 title='',
                 state='',
                 dimensions=None,
                 identifier_dimensions=None,
                 informational_dimensions=None,
                 imported_date='',
                 updated_date='',
                 collectors=[]):
        """
        Return entity object
        """
        self.title = title
        self.state = state
        self.dimensions = dimensions
        self.identifier_dimensions = identifier_dimensions
        self.informational_dimensions = informational_dimensions
        self.imported_date = imported_date
        self.updated_date = updated_date
        self._key = _key
        self.collectors = collectors
        if self._key is None:
            # Build _key field
            dims = {dim: self.dimensions[dim] for dim in identifier_dimensions}
            self._key = em_common.get_key_from_dims(dims)

    def get_raw_data(self):
        """
        Get raw dict object from this entity
        """
        logger.info('get raw entity data')
        return dict(
                    _key=self._key,
                    title=self.title,
                    state=self.state,
                    dimensions=self.dimensions,
                    identifier_dimensions=self.identifier_dimensions,
                    informational_dimensions=self.informational_dimensions,
                    imported_date=self.imported_date,
                    updated_date=self.updated_date,
                    collectors=self.collectors)

    def set_inactive(self):
        """
        Set this entity to store with inactive state
        """
        logger.info('set entity %s inactive', self.title)
        if self.state == 'disabled':
            return
        self.state = 'inactive'
