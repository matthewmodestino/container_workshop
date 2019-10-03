"""
Copyright (C) 2018 Splunk Inc. All Rights Reserved.
"""

from .base import BaseModel, Migrator
from .fields import DictField, ListField, NumberField, StringField
from .migrations.entity import migrations as entity_migrations


class Entity(BaseModel):
    """A common entity model to be shared across ITOA applications."""

    # The unique identifier for the entity
    unique_id = StringField(required=True)

    # The entity's title
    title = StringField(required=True)

    # A description for the entity
    description = StringField(default='')

    # Aliases that identify the entity
    aliases = DictField((basestring, list), default=lambda: {})

    # Informational data related to the entity
    informational = DictField((basestring, list), default=lambda: {})

    # The sources where the entity was discovered
    sources = ListField(basestring, default=lambda: [])

    # The time in seconds since epoch when the entity was created
    creation_time = NumberField()

    # The time in seconds since epoch when the entity was updated
    updated_time = NumberField()

    # Setup data migrations for different entity model versions
    migrator = Migrator(entity_migrations)
