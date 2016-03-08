# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from ansible.errors import AnsibleFilterError
from sys import version_info as py_version_info

PY3K = py_version_info >= (3, 0)
if PY3K:
    basestring = str

# ------------------------------------------------------------------------------
# FILTERS ----------------------------------------------------------------------

def mount_device(item):
    '''Get the mount device.
    It's a mandatory preference, except:
    - When the partition type is `tmp`.
    '''
    if item.get('type') == 'tmp':
        return 'tmpfs'
    else: # If it's not a particular case the `device` value must be set.
        return item['device']

def mount_path(item, root_dir='/'):
    '''Get the mount path.
    It's a mandatory preference, except:
    - When the filesystem is `swap`.
    '''
    if item.get('fs') == 'swap':
        return 'none'
    else:
        return '/'.join([root_dir, item['mount']['path']]).replace('//', '/')

def mount_fs(item):
    '''Get the mount filesystem.
    It's a mandatory preference, except:
    - When the type is `tmp`.
    If the filesystem is `fat*` it will be normalized to `vfat`.
    '''
    if item.get('type') == 'tmp':
        return 'tmpfs'
    elif item.get('fs', '').startswith('fat'):
        return 'vfat'
    else: # If it's not a particular case the `fs` value must be set.
        return item['fs']

def mount_opts(item):
    '''Get the mount options.
    It's a optional preference, but when it's given, it should be a
    comma-separated string or a list.
    If the filesystem is `swap`, it will be automatically computed.
    '''
    opts_value = None

    if item.get('mount', {}).get('opts'):
        print(item['mount'])
        if isinstance(item['mount']['opts'], list):
            opts_value = ','.join(item['mount']['opts'])
        elif isinstance(item['mount']['opts'], basestring):
            opts_value = item['mount']['opts']
        else:
            raise AnsibleFilterError('Cannot handle mount options')
    elif item.get('fs') == 'swap':
        opts_value = 'sw'
    else: # Default filesystem options.
        opts_value = 'defaults,relatime'
        if item.get('fs') in ['ext4', 'ext3']:
            opts_value += ',acl'

    return opts_value

def mount_backup(item):
    '''Get the mount backup preference.
    Default is `False`.
    '''
    dump_value = item.get('mount', {}).get('backup', False)
    if dump_value is True:
        return '1'
    elif dump_value is False:
        return '0'
    else:
        raise AnsibleFilterError('Invalid mount backup: not boolean')

def mount_check(item):
    '''Get the mount check preference.
    Default is check enabled with normal priority.
    '''
    min_check_value = 0
    max_check_value = 2
    check_value = int(item.get('mount', {}).get('check', 1))

    if check_value < min_check_value or check_value > max_check_value:
        raise AnsibleFilterError('Invalid mount check: not in ({},{})'.format(
                                 min_check_value, max_check_value))
    if item.get('fs') == 'btrfs' and check_value != 0:
        raise AnsibleFilterError("Filesystem `btfs` doesn't allow fs checking")

    return str(check_value)

def mount_state(item, states, default=None):
    '''Get the mount state looking up `states` based on item's type.
    '''
    state = states.get(item.get('type'), default)
    if not state in ['present', 'absent', 'mounted', 'unmounted']:
        raise AnsibleFilterError('Unsupported mount state')
    return state

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for mounting devices.'''

    def filters(self):
        return {'mount_device': mount_device,
                'mount_path':   mount_path,
                'mount_fs':     mount_fs,
                'mount_opts':   mount_opts,
                'mount_backup': mount_backup,
                'mount_check':  mount_check,
                'mount_state':  mount_state}
