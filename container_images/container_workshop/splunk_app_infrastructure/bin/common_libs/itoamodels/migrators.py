"""
Copyright (C) 2018 Splunk Inc. All Rights Reserved.
"""

from collections import OrderedDict
from copy import deepcopy


class MigrationError(Exception):
    """Raised when a data migration error occurs"""


class Migrator(object):
    """Handles data migrations from one version to others"""

    def __init__(self, migrate_funcs=None):
        """
        :param OrderedDict migrate_funcs: A dict of migration functions from version to migration function
        """
        if migrate_funcs is not None and not isinstance(migrate_funcs, OrderedDict):
            raise MigrationError('Migration functions should an ordered dictinoary from version to function')

        if migrate_funcs is None:
            migrate_funcs = OrderedDict()
        self.migrate_funcs = migrate_funcs

    def migrate(self, data):
        """
        Migrates the given data to the latest model schema version

        :param dict data: The data to migrate
        :return: The migrated data
        :rtype: dict
        """
        if not data or not isinstance(data, dict):
            return {}

        version = data.get('version', None)
        if not version or not isinstance(version, basestring):
            raise MigrationError('Model version not found')

        migrated = deepcopy(data)

        # This assumes that migrate funcs are already in an ordered fashion based on versions
        for key, func in self.migrate_funcs.items():
            if key < version:
                continue

            new_data = func(migrated)
            if new_data is None:
                raise MigrationError('Migration function should return a dictionary of data!')
            migrated = new_data

        return migrated
