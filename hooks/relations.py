# Copyright 2015 Canonical Ltd.
# Licensed under the GPLv3, see copyright file for details.

from charmhelpers.core import hookenv
from charmhelpers.core.services import helpers


class DbRelation(helpers.RelationContext):
    """Define the redis db relation."""

    name = 'db'
    interface = 'redis'

    def provide_data(self):
        """Return data to be relation_set for this interface."""
        config = hookenv.config()
        return {
            'hostname': hookenv.unit_get('public-address'),
            'port': config['port'],
            'password': config['password'].strip(),
        }


class MasterRelation(DbRelation):
    """Define the redis master relation."""

    name = 'master'


class SlaveRelation(helpers.RelationContext):
    """Define the redis slave relation."""

    name = 'slave'
    interface = 'redis'
    required_keys = ['hostname', 'port']
