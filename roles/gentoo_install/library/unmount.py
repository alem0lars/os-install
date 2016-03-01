#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from os.path import isfile as is_file

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: unmount
short_description: Unmount partitions and mapped devices
author:
    - "Alessandro Molari"
'''

EXAMPLES = '''
TODO
'''

# ------------------------------------------------------------------------------
# UNMOUNT POLICIES -------------------------------------------------------------

def unmount_mountpoints(module):
    ''' Unmount all (mounted) partitions.

    Partitions that can't be unmounted are those in use, so the command should
    work correctly (i.e. unmount only partitions of the current setup).
    '''
    module.run_command('umount -a')
    return [{'type': 'active mountpoints'}]

def unmount_lvm(module):
    module.run_command('vgchange -a n', check_rc=True)
    return [{'type': 'lvm'}]

def unmount_encryption(module):
    result = []

    _, out, _ = module.run_command('dmsetup info -c -o name', check_rc=True)
    lines = [line for line in out.split('\n') if line]
    if len(lines) > 1: # There is at least one device.
        enc_names = map(str.strip, lines[1:])
        for enc_name in enc_names:
            module.run_command('cryptsetup luksClose {}'.format(enc_name),
                               check_rc=True)
            result.append({'type': 'encryption', 'name': enc_name})

    return result

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec={
            'encryption': dict(type='bool', default=True),
            'lvm':        dict(type='bool', default=True),
        })

    unmounted = [] # Informations about unmounted volumes.

    unmounted += unmount_mountpoints(module)

    if module.params['lvm']:
        unmounted += unmount_lvm(module)

    if module.params['encryption']:
        unmounted += unmount_encryption(module)

    module.exit_json(changed=True, msg='Unmount success.', unmounted=unmounted)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
