# Overview

Redis (<http://redis.io>) is an open source, advanced key-value cache and
store. It is often referred to as a data structure server since keys can
contain strings, hashes, lists, sets, sorted sets, bitmaps and hyperloglogs.
In order to achieve its outstanding performance, Redis works with an in-memory
dataset that can be written to disk. Redis also supports master-slave
asynchronous replication.

Redis can be configured in a master or slave configuration.  This charm
provides a single stand alone master implementation of Redis software. Go to
the Redis web pages for more information on
[replication](http://redis.io/topics/replication).

# Usage

To deploy this charm first bootstrap your Juju environment and issue the
following command:

    juju deploy redis


Expose the master if you need to contact them for some reason.

    juju expose redis


# Replication

Redis can be set up with master-slave replication in Juju.  This allows the
Redis slave to be an exact copy of master server.  A master can have multiple
slaves.

See the [redis-slave](http://manage.jujucharms.com/charms/precise/redis-slave)
charm for more details about how to configure the Juju charms with replication.

# Testing Redis

To test if Redis software is functioning properly telnet to the redis ip
address using port 6379:

    telnet <redis-ip> 6379

You can also install the redis-tools package `apt-get install redis-tools`
and connect using the Redis client command:

    redis-cli

From there you can issue [Redis commands](http://redis.io/commands) to test
that Redis is working as intended.

## Known Limitations and Issues

If you run into problems or issues:

Go to the [issue database on github](https://github.com/antirez/redis/issues)
to check for problems related to the Redis software.

Go to the
[redis page on launchpad](https://bugs.launchpad.net/charms/+source/redis) to
check for redis related bugs.

The Redis log file can be found on the deployed instance at:
`/var/log/redis/redis-server.log`

## Contact Information

The charm was originally created by Juan Negron <juan.negron@canonical.com>

# Redis Information

- Redis [home page](http://redis.io/)
- Redis [github bug tracker](https://github.com/antirez/redis/issues)
- Redis [documentation](http://redis.io/documentation)
- Redis [mailing list](http://groups.google.com/group/redis-db)
- Using IRC join the #redis channel on Freenode ([web access link](http://webchat.freenode.net/?channels=redis))
