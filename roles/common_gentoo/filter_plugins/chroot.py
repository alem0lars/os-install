# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from ansible.errors import AnsibleFilterError

# ------------------------------------------------------------------------------
# COMMONS (generated) <chrooted> -----------------------------------------------

def chrooted(command, path, profile='/etc/profile', work_dir=None):
    prefix = "chroot {path} bash -c 'source {profile}; ".format(
        path=path, profile=profile)
    if work_dir:
        prefix += 'cd {work_dir}; '.format(work_dir=work_dir)
    prefix += command
    prefix += "'"
    return prefix

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for working with remote chroot environments.'''

    def filters(self):
        return {'chrooted': chrooted}

# ------------------------------------------------------------------------------
# vim: set filetype=python :
