# Copyright 2015 Canonical Ltd.
# Licensed under the GPLv3, see copyright file for details.

from charmhelpers.core import (
    hookenv,
    host,
)

import configfile


# Define the name of the init service set up when installing redis.
SERVICE_NAME = 'redis-server'


def service_start(service_name):
    """Start the service if not already running."""
    if not host.service_running(SERVICE_NAME):
        hookenv.log('Starting service {}.'.format(service_name))
        host.service_start(SERVICE_NAME)


def service_stop(service_name):
    """Stop the service if it is running and if the stop hook is executing."""
    if hookenv.hook_name() == 'stop' and host.service_running(SERVICE_NAME):
        # There is no need to stop the service if we are not in the stop hook.
        hookenv.log('Stopping service {}.'.format(service_name))
        host.service_stop(SERVICE_NAME)
        # XXX (frankban): remove redis package and clean up files.


def write_config_file(
        config, db_relation=None, master_relation=None, slave_relation=None):
    """Wrap the configfile.write function building options for the config.

    The config argument is the hook environment configuration.
    The slave_relation argument is the redis-slave relation context, assumed to
    be ready.

    Return a function that can be used as a callback in the services framework,
    and that generates the redis configuration file.

    This returned functions also takes care of restarting the service if the
    configuration changed.
    """
    def callback(service_name):
        options = _get_service_options(config, slave_relation)
        hookenv.log('Writing configuration file for {}.'.format(service_name))
        changed = configfile.write(options, configfile.REDIS_CONF)
        if changed:
            hookenv.log('Restarting service due to configuration change.')
            host.service_restart(SERVICE_NAME)
            # If the configuration changed, it is possible that related units
            # require notification of changes. For this reason, update all the
            # existing established relations. This is required because
            # "services.provide_data" is only called when the current hook
            # is a relation joined or changed.
            _update_relations(filter(None, [db_relation, master_relation]))
        else:
            hookenv.log('No changes detected in the configuration file.')

    return callback


def _get_service_options(config, slave_relation=None):
    """Return a dict containing the redis service configuration options.

    Receive the hook environment config object.
    """
    hookenv.log('Retrieving service options.')
    # To introduce more redis configuration options in the charm, add them to
    # the config.yaml file and to the dictionary returned by this function.
    # If the new options are relevant while establishing relations, also update
    # the "provide_data" methods in the relation contexts defined in
    # relations.py.
    options = {
        'bind': hookenv.unit_get('public-address'),
        'logfile': config['logfile'],
        'loglevel': config['loglevel'],
        'port': config['port'],
    }
    password = config['password'].strip()
    if password:
        options['requirepass'] = password
    if slave_relation is not None:
        hookenv.log('Setting up slave relation.')
        # If slave_relation is defined, it is assumed that the relation is
        # ready, i.e. that the slave_relation dict evaluates to True.
        data = slave_relation[slave_relation.name][0]
        options['slaveof'] = '{hostname} {port}'.format(**data)
        password = data.get('password')
        if password:
            options['masterauth'] = password
    return options


def _update_relations(relations):
    """Update existing established relations."""
    for relation in relations:
        for relation_id in hookenv.relation_ids(relation.name):
            hookenv.log('Updating data for relation {}.'.format(relation.name))
            hookenv.relation_set(relation_id, relation.provide_data())
