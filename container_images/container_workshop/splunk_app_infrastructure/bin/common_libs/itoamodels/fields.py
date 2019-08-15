"""
Copyright (C) 2018 Splunk Inc. All Rights Reserved.
"""

class FieldValidationError(Exception):
    """Raised when a field fails to validate its value"""

    def __init__(self, value):
        """
        :param str value: the exception's error message value
        """
        super(FieldValidationError, self).__init__()
        self.value = value

    def __str__(self):
        """
        :return: the error message value
        :rtype: str
        """
        return repr(self.value)


class BaseField(object):
    """A base implementation class for a model's field definition"""

    def __init__(self, required=False, default=None):
        self.required = True if required else False
        self.default = default

    def validate(self, value):
        """
        Validates the given value based on the current field type

        :param value: the value to validate
        """
        if self.required and value is None:
            raise FieldValidationError('is required')


class StringField(BaseField):
    """A field that validates string values"""

    def validate(self, value):
        """
        Validates that the given value is a string

        :param value: the value to validate
        """
        super(StringField, self).validate(value)

        if value is not None and not isinstance(value, basestring):
            raise FieldValidationError('should be string')


class NumberField(BaseField):
    """A field that validates number values"""

    def validate(self, value):
        """
        Validates that the given value is a number

        :param value: the value to validate
        """
        super(NumberField, self).validate(value)

        if value is not None and not isinstance(value, (int, float)):
            raise FieldValidationError('should be number')


class CompoundField(BaseField):
    def __init__(self, subtype=None, *args, **kwargs):
        super(CompoundField, self).__init__(*args, **kwargs)
        self.subtype = subtype


class DictField(CompoundField):
    """A field that validates dict values"""

    def validate(self, value):
        """
        Validates that the given value is a dict

        :param value: the value to validate
        """
        super(DictField, self).validate(value)

        if value is not None and not isinstance(value, dict):
            raise FieldValidationError('should be dict')

        self._validate_values_type(value)

    def _validate_values_type(self, value):
        """
        Validates that the inner values have the correct type

        :param value: the iterable value to validate
        """
        if not value or self.subtype is None:
            return

        for val in value.values():
            if val is not None and not isinstance(val, self.subtype):
                raise FieldValidationError('should have all {} values'.format(self.subtype))


class ListField(CompoundField):
    """A field that validates list values"""

    def validate(self, value):
        """
        Validates that the given value is a list

        :param value: the value to validate
        """
        super(ListField, self).validate(value)

        if value is not None and not isinstance(value, list):
            raise FieldValidationError('should be list')

        self._validate_values_type(value)

    def _validate_values_type(self, value):
        """
        Validates that the inner values have the correct type

        :param value: the iterable value to validate
        """
        if not value or self.subtype is None:
            return

        for val in value:
            if val is not None and not isinstance(val, self.subtype):
                raise FieldValidationError('should have all {} values'.format(self.subtype))
