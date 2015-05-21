# Copyright 2015 Canonical Ltd.
# Licensed under the GPLv3, see copyright file for details.

import functools

from charmhelpers.core import hookenv


def hook_name_logged(function):
    """Decorate the given function so that the current hook name is logged.

    The given function is assumed to not accept any arguments.
    """
    @functools.wraps(function)
    def decorated():
        hook_name = hookenv.hook_name()
        hookenv.log('>>> Entering hook: {}.'.format(hook_name))
        try:
            return function()
        finally:
            hookenv.log('<<< Exiting hook: {}.'.format(hook_name))
    return decorated
