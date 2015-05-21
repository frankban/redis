#!/usr/bin/env python3

# Copyright 2015 Canonical Ltd.
# Licensed under the GPLv3, see copyright file for details.

# These tests use the Amulet test helpers:
# see https://jujucharms.com/docs/stable/tools-amulet

import itertools
from pkg_resources import resource_filename
import sys
import telnetlib
import unittest

import amulet

# Allow importing modules and packages from the hooks directory.
sys.path.append(resource_filename(__name__, '../hooks'))

import configfile


# Define the charm name.
CHARM_NAME = 'redis'


class RedisClient(object):
    """A very simple and naive telnet redis client used for tests."""

    def __init__(self, host, port=6379):
        """Initialize the client."""
        self._host = host
        self._port = port
        self._client = None

    def connect(self, password=None):
        """Connect to the client."""
        self._client = telnetlib.Telnet(self._host, self._port)
        if password is not None:
            self._client.write('AUTH {}\n'.format(password))
            response = self._readline()
            if response != '+OK':
                raise ValueError('authentication error: {}'.format(response))

    def close(self):
        """Close the client connection."""
        if self._client is not None:
            self._client.close()
        self._client = None

    def set(self, key, value):
        """Set a key in the redis database, with the given value."""
        self._client.write('SET {} {}\n'.format(key, value))
        response = self._readline()
        if response != '+OK':
            raise ValueError('unexpected response: {}'.format(response))

    def get(self, key):
        """Return the value corresponding to key from the redis database.

        Return None if the key is not found.
        """
        self._client.write('GET {}\n'.format(key))
        response = self._readline()
        if response == '$-1':
            return None
        return self._readline()

    def _readline(self):
        """Read next line from the client connection."""
        return self._client.read_until('\r\n').strip()


_counter = itertools.count()


def get_service_name():
    """Return an incremental redis service name."""
    return 'redis{}'.format(next(_counter))


def deploy(options=None):
    """Deploy one unit of the given service using the redis charm.

    Return the Amulet deployment and the unit object.
    """
    deployment = amulet.Deployment(series='trusty')
    service_name = get_service_name()
    deployment.add(service_name, charm=CHARM_NAME)
    if options is not None:
        deployment.configure(service_name, options)
    deployment.expose(service_name)
    try:
        deployment.setup(timeout=900)
        deployment.sentry.wait()
    except amulet.helpers.TimeoutError:
        amulet.raise_status(
            amulet.FAIL, msg='Environment was not stood up in time.')
    return deployment, deployment.sentry.unit[service_name + '/0']


def deploy_master_slave(master_options=None, slave_options=None):
    """Deploy two redis services related in a master-slave relationship.

    The services are called "redis1" and "redis2".

    Return the Amulet deployment and the two unit objects.
    """
    deployment = amulet.Deployment(series='trusty')
    master, slave = get_service_name(), get_service_name()
    deployment.add(master, charm=CHARM_NAME)
    deployment.add(slave, charm=CHARM_NAME)
    if master_options is not None:
        deployment.configure(master, master_options)
    if slave_options is not None:
        deployment.configure(slave, slave_options)
    deployment.relate(master + ':master', slave + ':slave')
    deployment.expose(master)
    deployment.expose(slave)
    try:
        deployment.setup(timeout=900)
        deployment.sentry.wait()
    except amulet.helpers.TimeoutError:
        amulet.raise_status(
            amulet.FAIL, msg='Environment was not stood up in time.')
    units = deployment.sentry.unit
    return deployment, units[master + '/0'], units[slave + '/0']


class TestDeployment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Set up the environment and deploy the charm.
        cls.deployment, cls.unit = deploy()

    @classmethod
    def tearDownClass(cls):
        # Remove the redis service.
        cls.deployment.remove_service(cls.unit.info['service'])

    def test_config_file(self):
        expected_content = (
            'bind {}\n'
            'logfile /var/log/redis/redis-server.log\n'
            'loglevel notice\n'
            'port 6379\n'
        ).format(self.unit.info['public-address'])
        self.assertEqual(
            expected_content,
            self.unit.file_contents(configfile.REDIS_CONF))

    def test_connection(self):
        client = RedisClient(self.unit.info['public-address'])
        client.connect()
        self.addCleanup(client.close)
        self.assertIsNone(client.get('my-key'))
        client.set('my-key', 'my-value')
        self.assertEqual('my-value', client.get('my-key'))


class TestDeploymentOptions(unittest.TestCase):

    options = {
        'port': 4242,
        'password': 'secret',
        'loglevel': 'verbose',
        'logfile': '/tmp/redis.log',
    }

    @classmethod
    def setUpClass(cls):
        # Set up the environment and deploy the charm.
        cls.deployment, cls.unit = deploy(options=cls.options)

    @classmethod
    def tearDownClass(cls):
        # Remove the redis service.
        cls.deployment.remove_service(cls.unit.info['service'])

    def test_config_file(self):
        expected_content = (
            'bind {}\n'
            'logfile /tmp/redis.log\n'
            'loglevel verbose\n'
            'port 4242\n'
            'requirepass secret\n'
        ).format(self.unit.info['public-address'])
        self.assertEqual(
            expected_content,
            self.unit.file_contents(configfile.REDIS_CONF))

    def test_connection(self):
        client = RedisClient(
            self.unit.info['public-address'], port=self.options['port'])
        client.connect(password=self.options['password'])
        self.addCleanup(client.close)
        self.assertIsNone(client.get('my-key'))
        client.set('my-key', 'my-value')
        self.assertEqual('my-value', client.get('my-key'))


class TestMasterSlaveRelation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Set up the environment and deploy the charm.
        cls.deployment, cls.master, cls.slave = deploy_master_slave()

    @classmethod
    def tearDownClass(cls):
        # Remove the redis master and slave services.
        cls.deployment.remove_service(cls.slave.info['service'])
        cls.deployment.remove_service(cls.master.info['service'])

    def test_master_config_file(self):
        expected_content = (
            'bind {}\n'
            'logfile /var/log/redis/redis-server.log\n'
            'loglevel notice\n'
            'port 6379\n'
        ).format(self.master.info['public-address'])
        self.assertEqual(
            expected_content,
            self.master.file_contents(configfile.REDIS_CONF))

    def test_slave_config_file(self):
        expected_content = (
            'bind {}\n'
            'logfile /var/log/redis/redis-server.log\n'
            'loglevel notice\n'
            'port 6379\n'
            'slaveof {} 6379\n'
        ).format(
            self.slave.info['public-address'],
            self.master.info['public-address'])
        self.assertEqual(
            expected_content,
            self.slave.file_contents(configfile.REDIS_CONF))

    def test_connection(self):
        master_client = RedisClient(self.master.info['public-address'])
        master_client.connect()
        self.addCleanup(master_client.close)
        master_client.set('my-key', '42')
        # Retrieve the value from the slave.
        slave_client = RedisClient(self.slave.info['public-address'])
        slave_client.connect()
        self.addCleanup(slave_client.close)
        self.assertEqual('42', slave_client.get('my-key'))


class TestMasterSlaveRelationOptions(unittest.TestCase):

    master_options = {'password': 'secret'}
    slave_options = {'port': 4747, 'loglevel': 'warning'}

    @classmethod
    def setUpClass(cls):
        # Set up the environment and deploy the charm.
        cls.deployment, cls.master, cls.slave = deploy_master_slave(
            master_options=cls.master_options,
            slave_options=cls.slave_options)

    @classmethod
    def tearDownClass(cls):
        # Remove the redis master and slave services.
        cls.deployment.remove_service(cls.slave.info['service'])
        cls.deployment.remove_service(cls.master.info['service'])

    def test_master_config_file(self):
        expected_content = (
            'bind {}\n'
            'logfile /var/log/redis/redis-server.log\n'
            'loglevel notice\n'
            'port 6379\n'
            'requirepass secret\n'
        ).format(self.master.info['public-address'])
        self.assertEqual(
            expected_content,
            self.master.file_contents(configfile.REDIS_CONF))

    def test_slave_config_file(self):
        expected_content = (
            'bind {}\n'
            'logfile /var/log/redis/redis-server.log\n'
            'loglevel warning\n'
            'masterauth secret\n'
            'port 4747\n'
            'slaveof {} 6379\n'
        ).format(
            self.slave.info['public-address'],
            self.master.info['public-address'])
        self.assertEqual(
            expected_content,
            self.slave.file_contents(configfile.REDIS_CONF))

    def test_connection(self):
        master_client = RedisClient(self.master.info['public-address'])
        master_client.connect(password=self.master_options['password'])
        self.addCleanup(master_client.close)
        master_client.set('my-key', '42')
        # Retrieve the value from the slave.
        slave_client = RedisClient(
            self.slave.info['public-address'], port=self.slave_options['port'])
        slave_client.connect()
        self.addCleanup(slave_client.close)
        self.assertEqual('42', slave_client.get('my-key'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
