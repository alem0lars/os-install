#!/usr/bin/python
# -*- coding: utf-8 -*-
# IMPORTS ----------------------------------------------------------------------

from ansible.errors import AnsibleFilterError

# ------------------------------------------------------------------------------
# FILTERS ----------------------------------------------------------------------

def mount_path(item, root_dir='/'):
    if item.fs == 'swap':
        return 'none'
    else:
        return [root_dir, item.mount.path].join('/')

def mount_fs(item):
    if item.fs.startswith('fat'):
        return 'vfat'
    else:
        return item.fs

def mount_opts(item):
    opts_value = None

    if 'opts' in item.mount:
        if isinstance(item.mount.opts, list):
            opts_value = ','.join(item.mount.opts)
        elif isinstance(item.mount.opts, basestring):
            opts_value = item.mount.opts
        else:
            raise AnsibleFilterError('Cannot handle mount options')

    if item.fs == 'swap':
        opts_value = 'sw'
    else:
        opts_value = 'defaults,relatime'
        if item.fs in ['ext4', 'ext3']:
            opts_value += ',acl'

    return opts_value

def mount_backup(item):
    dump_value = item.mount.backup
    if dump_value is True:
        return 1
    elif dump_value is False:
        return 0
    else:
        raise AnsibleFilterError('Invalid mount backup: not boolean')

def mount_check(item):
    min_check_value = 0
    max_check_value = 2
    check_value = int(item.mount.check)

    if check_value < min_check_value or check_value > max_check_value:
        raise AnsibleFilterError('Invalid mount check: not in ({},{})'.format(
                                 min_check_value, max_check_value))
    if item.fs == 'btrfs' and check_value != 0:
        raise AnsibleFilterError("Filesystem `btfs` doesn't allow fs checking")

    return check_value

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for mounting devices.'''

    def filters(self):
        return {
            'mount_path':   mount_path,
            'mount_fs':     mount_fs,
            'mount_opts':   mount_opts,
            'mount_backup': mount_backup,
            'mount_check':  mount_check,
        }
