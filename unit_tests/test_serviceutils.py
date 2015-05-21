# Copyright 2015 Canonical Ltd.
# Licensed under the GPLv3, see copyright file for details.

import contextlib
from pkg_resources import resource_filename
import sys
import unittest

import mock

# Allow importing modules and packages from the hooks directory.
sys.path.append(resource_filename(__name__, '../hooks'))

import configfile
import serviceutils


def patch_service_running(value):
    """Patch the "charmhelpers.core.host.service_running" function.

    The mocked function returns the given value.
    """
    return mock.patch(
        'charmhelpers.core.host.service_running',
        lambda service_name: value)


def patch_hook_name(value):
    """Patch the "charmhelpers.core.hookenv.hook_name" function.

    The mocked function returns the given value.
    """
    return mock.patch('charmhelpers.core.hookenv.hook_name', lambda: value)


@mock.patch('charmhelpers.core.host.service_start')
@mock.patch('charmhelpers.core.hookenv.log')
class TestServiceStart(unittest.TestCase):

    def test_not_running(self, mock_log, mock_service_start):
        with patch_service_running(False):
            serviceutils.service_start('foo')
        mock_service_start.assert_called_once_with(serviceutils.SERVICE_NAME)
        mock_log.assert_called_once_with('Starting service foo.')

    def test_already_running(self, mock_log, mock_service_start):
        with patch_service_running(True):
            serviceutils.service_start('foo')
        self.assertFalse(mock_service_start.called)
        self.assertFalse(mock_log.called)


@mock.patch('charmhelpers.core.host.service_stop')
@mock.patch('charmhelpers.core.hookenv.log')
class TestServiceStop(unittest.TestCase):

    def test_service_running_stop_hook(self, mock_log, mock_service_stop):
        with patch_service_running(True):
            with patch_hook_name('stop'):
                serviceutils.service_stop('foo')
        mock_service_stop.assert_called_once_with(serviceutils.SERVICE_NAME)
        mock_log.assert_called_once_with('Stopping service foo.')

    def test_service_not_running_stop_hook(self, mock_log, mock_service_stop):
        with patch_service_running(False):
            with patch_hook_name('stop'):
                serviceutils.service_stop('foo')
        self.assertFalse(mock_service_stop.called)
        self.assertFalse(mock_log.called)

    def test_service_running_other_hook(self, mock_log, mock_service_stop):
        with patch_service_running(True):
            with patch_hook_name('config-changed'):
                serviceutils.service_stop('foo')
        self.assertFalse(mock_service_stop.called)
        self.assertFalse(mock_log.called)

    def test_service_not_running_other_hook(self, mock_log, mock_service_stop):
        with patch_service_running(False):
            with patch_hook_name('config-changed'):
                serviceutils.service_stop('foo')
        self.assertFalse(mock_service_stop.called)
        self.assertFalse(mock_log.called)


def make_relation(data):
    """Create and return a mock relation with the given data."""
    relation = type('Relation', (dict,), {
        'name': 'testing',
        'provide_data': lambda self: data,
    })()
    relation['testing'] = [data]
    return relation


class TestWriteConfigFile(unittest.TestCase):

    @contextlib.contextmanager
    def patch_all(self, configuration_changed=False):
        """Mock all the external functions used by write_config_file."""
        mocks = {
            'log': mock.patch('charmhelpers.core.hookenv.log'),
            'relation_ids': mock.patch(
                'charmhelpers.core.hookenv.relation_ids',
                mock.Mock(return_value=['rel-id'])),
            'relation_set': mock.patch(
                'charmhelpers.core.hookenv.relation_set'),
            'service_restart': mock.patch(
                'charmhelpers.core.host.service_restart'),
            'unit_get': mock.patch(
                'charmhelpers.core.hookenv.unit_get',
                mock.Mock(return_value='1.2.3.4')),
            'write': mock.patch(
                'configfile.write',
                mock.Mock(return_value=configuration_changed))
        }
        # Note: nested is deprecated for good reasons which do not apply here.
        # Used here to easily nest a dynamically generated list of context
        # managers.
        with contextlib.nested(*mocks.values()) as context_managers:
            object_dict = dict(zip(mocks.keys(), context_managers))
            yield type('Mocks', (object,), object_dict)

    def test_configuration_changed(self):
        config = {
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'password': '',
            'port': 4242,
        }
        callback = serviceutils.write_config_file(config)
        with self.patch_all(configuration_changed=True) as mocks:
            callback('foo')
        mocks.write.assert_called_once_with({
            'bind': '1.2.3.4',
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'port': 4242,
        }, configfile.REDIS_CONF)
        mocks.unit_get.assert_called_once_with('public-address')
        mocks.service_restart.assert_called_once_with(
            serviceutils.SERVICE_NAME)
        self.assertEqual(3, mocks.log.call_count)
        mocks.log.assert_has_calls([
            mock.call('Retrieving service options.'),
            mock.call('Writing configuration file for foo.'),
            mock.call('Restarting service due to configuration change.')
        ])

    def test_configuration_changed_password(self):
        config = {
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'password': 'secret!',
            'port': 4242,
        }
        callback = serviceutils.write_config_file(config)
        with self.patch_all(configuration_changed=True) as mocks:
            callback('foo')
        mocks.write.assert_called_once_with({
            'bind': '1.2.3.4',
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'port': 4242,
            'requirepass': 'secret!',
        }, configfile.REDIS_CONF)
        mocks.unit_get.assert_called_once_with('public-address')
        mocks.service_restart.assert_called_once_with(
            serviceutils.SERVICE_NAME)

    def test_configuration_changed_relations(self):
        config = {
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'password': 'secret!',
            'port': 4242,
        }
        data = {
            'hostname': '4.3.2.1',
            'port': 90,
        }
        db_relation = make_relation(data)
        callback = serviceutils.write_config_file(
            config, db_relation=db_relation)
        with self.patch_all(configuration_changed=True) as mocks:
            callback('foo')
        mocks.write.assert_called_once_with({
            'bind': '1.2.3.4',
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'port': 4242,
            'requirepass': 'secret!',
        }, configfile.REDIS_CONF)
        mocks.unit_get.assert_called_once_with('public-address')
        mocks.service_restart.assert_called_once_with(
            serviceutils.SERVICE_NAME)
        mocks.relation_ids.assert_called_once_with('testing')
        mocks.relation_set.assert_called_once_with('rel-id', data)

    def test_configuration_unchanged_master(self):
        config = {
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'password': '',
            'port': 4242,
        }
        callback = serviceutils.write_config_file(config)
        with self.patch_all() as mocks:
            callback('foo')
        mocks.write.assert_called_once_with({
            'bind': '1.2.3.4',
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'port': 4242,
        }, configfile.REDIS_CONF)
        mocks.unit_get.assert_called_once_with('public-address')
        self.assertFalse(mocks.service_restart.called)
        self.assertEqual(3, mocks.log.call_count)
        mocks.log.assert_has_calls([
            mock.call('Retrieving service options.'),
            mock.call('Writing configuration file for foo.'),
            mock.call('No changes detected in the configuration file.')
        ])

    def test_configuration_unchanged_slave(self):
        config = {
            'logfile': '/path/to/logs',
            'loglevel': 'info',
            'password': '   ',
            'port': 4242,
        }
        slave_relation = make_relation({
            'hostname': '4.3.2.1',
            'port': 4747,
        })
        callback = serviceutils.write_config_file(
            config, slave_relation=slave_relation)
        with self.patch_all() as mocks:
            callback('foo')
        mocks.write.assert_called_once_with({
            'bind': '1.2.3.4',
            'logfile': '/path/to/logs',
            'loglevel': 'info',
            'port': 4242,
            'slaveof': '4.3.2.1 4747'
        }, configfile.REDIS_CONF)
        mocks.unit_get.assert_called_once_with('public-address')
        self.assertFalse(mocks.service_restart.called)
        self.assertEqual(4, mocks.log.call_count)
        mocks.log.assert_has_calls([
            mock.call('Retrieving service options.'),
            mock.call('Setting up slave relation.'),
            mock.call('Writing configuration file for foo.'),
            mock.call('No changes detected in the configuration file.')
        ])

    def test_configuration_unchanged_master_password(self):
        config = {
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'password': 'secret!',
            'port': 42,
        }
        callback = serviceutils.write_config_file(config)
        with self.patch_all() as mocks:
            callback('foo')
        mocks.write.assert_called_once_with({
            'bind': '1.2.3.4',
            'logfile': '/path/to/logfile',
            'loglevel': 'debug',
            'port': 42,
            'requirepass': 'secret!',
        }, configfile.REDIS_CONF)
        mocks.unit_get.assert_called_once_with('public-address')
        self.assertFalse(mocks.service_restart.called)

    def test_configuration_unchanged_slave_password(self):
        config = {
            'logfile': '/path/to/logs',
            'loglevel': 'info',
            'password': '',
            'port': 4242,
        }
        slave_relation = make_relation({
            'hostname': '4.3.2.1',
            'password': 'sercret!',
            'port': 90,
        })
        callback = serviceutils.write_config_file(
            config, slave_relation=slave_relation)
        with self.patch_all() as mocks:
            callback('foo')
        mocks.write.assert_called_once_with({
            'bind': '1.2.3.4',
            'logfile': '/path/to/logs',
            'loglevel': 'info',
            'masterauth': 'sercret!',
            'port': 4242,
            'slaveof': '4.3.2.1 90'
        }, configfile.REDIS_CONF)
        mocks.unit_get.assert_called_once_with('public-address')
        self.assertFalse(mocks.service_restart.called)
