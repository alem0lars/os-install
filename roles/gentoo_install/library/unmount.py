#!/usr/bin/python
# -*- coding: utf-8 -*-

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
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec={
            'encryption': dict(type='bool', default=True),
            'lvm':        dict(type='bool', default=True),
        })

    unmounted = [] # Informations about unmounted volumes.

    # Unmount all (mounted) partitions. Partitions that can't be unmounted are
    # those in use, so the command should work correctly (i.e. unmount only
    # partitions we regarding the current setup).
    module.run_command('umount -a')
    unmounted.append({'type': 'active mountpoints'})

    if module.params['lvm']:
        module.run_command('vgchange -a n', check_rc=True)
        unmounted.append({'type': 'lvm'})

    if module.params['encryption']:
        _, out, _ = module.run_command('dmsetup info -c -o name', check_rc=True)
        lines = filter(None, out.split('\n'))
        if len(lines) > 1: # There is at least one device.
            enc_names = map(str.strip, lines[1:])
            for enc_name in enc_names:
                module.run_command('cryptsetup luksClose {}'.format(enc_name),
                                   check_rc=True)
                unmounted.append({'type': 'encryption', 'name': enc_name})

    module.exit_json(changed=True, msg='Unmount success.', unmounted=unmounted)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
