# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from ansible.errors import AnsibleFilterError

# ------------------------------------------------------------------------------
# CUSTOM COMMANDS BUILDERS -----------------------------------------------------

def make(opts, directory=None):
    if not isinstance(opts, list):
        opts = [opts]
    cmd = "make {opts}".format(opts=' '.join(opts))
    if dir is not None:
        cmd = 'cd {directory}; {cmd}'.format(directory=directory, cmd=cmd)
    return cmd

def make_kernel(opts, name='linux'):
    return make(opts, directory='/usr/src/{name}'.format(name=name))

def emerge(package):
    return "emerge {package}".format(package=package)

# ------------------------------------------------------------------------------
# MISC -------------------------------------------------------------------------

def chrooted(command, path='/mnt/gentoo', profile='/etc/profile'):
    return "chroot {path} bash -c 'source {profile}; {command}'".format(
        path=path, profile=profile, command=command)

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for working with remote chroot environments.'''

    def filters(self):
        return {'make':        make,
                'make_kernel': make_kernel,
                'emerge':      emerge,
                'chrooted':    chrooted}
