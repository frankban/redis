# Copyright 2015 Canonical Ltd.
# Licensed under the GPLv3, see copyright file for details.


def pre_install():
    """Do any setup required before the install hook."""
    install_charmhelpers()


def install_charmhelpers():
    """Install the charmhelpers library, if not present."""
    try:
        import charmhelpers  # noqa
    except ImportError:
        import subprocess
        subprocess.check_call(['apt-get', 'install', '-y', 'python-pip'])
        subprocess.check_call(['pip', 'install', 'charmhelpers==0.3.1'])
