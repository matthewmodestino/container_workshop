"""
Copyright (C) 2018 Splunk Inc. All Rights Reserved.
"""

import json

from .fields import BaseField, FieldValidationError, StringField
from .migrators import Migrator


def get_schema_version():
    """
    Returns the current schema version

    :return: the schema version
    :rtype: str
    """
    from . import __version__
    return __version__


class ValidationError(Exception):
    """Raised when a data or validation error occurs on the model"""


class BaseModel(object):
    """A base model implementation that provides additional helper functionality."""

    # Helper object to handle data migrations between different model versions
    migrator = Migrator()

    # The model version
    version = StringField(default=get_schema_version, required=True)

    def __init__(self, data=None, auto_validate=True, auto_migrate=True):
        """
        :param dict data: The model data
        :param auto_validate bool: Whether to automatically call validate on the model
        :param auto_migrate bool: Whether to automatically migrate the model's data to the latest model version
        """
        if data is None:
            data = {}

        if data.get('version', None) is None:
            data['version'] = self.version.default()

        if auto_migrate:
            data = self.migrator.migrate(data)

        self._fields = self._extract_fields()
        self._populate_model(self._fields, data)

        if auto_validate:
            self.validate()

    def validate(self):
        """
        Validates the current model based on its schema of fields.
        """
        for name, field in self._fields.iteritems():
            value = getattr(self, name)
            try:
                field.validate(value)
            except FieldValidationError, ex:
                raise ValidationError('"{}" {}'.format(name, ex))

    def raw_data(self):
        """
        Returns a dict obj that represents the current model

        :return: a dict
        :rtype: dict
        """
        obj = {}
        for name in self._fields.keys():
            obj[name] = getattr(self, name)
        return obj

    def json(self):
        """
        Returns a JSON string that represents the current model

        :return: a JSON string
        :rtype: str
        """
        return json.dumps(self.raw_data())

    def _extract_fields(self):
        """
        Returns a mapping dict of field name to field types

        :return: a dict from str to an instance of BaseField
        :rtype: dict
        """
        fields = {}

        class_items = BaseModel.__dict__.items() + self.__class__.__dict__.items()
        for name, value in class_items:
            if not isinstance(value, BaseField):
                continue
            fields[name] = value

        return fields

    def _populate_model(self, fields, data):
        """
        Populates the model with values from data for each field

        :param dict fields: a dict from field name to BaseField
        :param dict data: a dict from field name to data value
        """
        for name, field in fields.iteritems():
            default = field.default
            value = data.get(name, None)

            if value is None and default is not None:
                value = default() if callable(default) else default

            setattr(self, name, value)
