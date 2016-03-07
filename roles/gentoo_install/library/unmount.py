#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import re

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
- name: Unmount pre-existing partitions and mapped devices
  unmount:
    basic:      /mnt/gentoo
    encryption: true
    lvm:        true
'''

# ------------------------------------------------------------------------------
# COMMONS (generated) <BaseObject, chrooted> -----------------------------------

class BaseObject(object):
    import syslog, os

    '''Base class for all classes that use AnsibleModule.
    Dependencies:
    - `chrooted` function.
    '''
    def __init__(self, module, params=None):
        syslog.openlog('ansible-{module}-{name}'.format(
            module=os.path.basename(__file__), name=self.__class__.__name__))
        self.work_dir = None
        self.chroot = None
        self._module = module
        self._command_prefix = None
        if params:
            self._parse_params(params)

    @property
    def command_prefix(self):
        return self._command_prefix

    @command_prefix.setter
    def command_prefix(self, value):
        self._command_prefix = value

    def run_command(self, command=None, **kwargs):
        if not 'check_rc' in kwargs:
            kwargs['check_rc'] = True
        if command is None and self.command_prefix is None:
            self.fail('Invalid command')
        if self.command_prefix:
            command = '{prefix} {command}'.format(
                prefix=self.command_prefix, command=command or '')
        if self.work_dir and not self.chroot:
            command = 'cd {work_dir}; {command}'.format(
                work_dir=self.work_dir, command=command)
        if self.chroot:
            command = chrooted(command, self.chroot, work_dir=self.work_dir)
        self.log('Performing command `{}`'.format(command))
        rc, out, err = self._module.run_command(command, **kwargs)
        if rc != 0:
            self.log('Command `{}` returned invalid status code: `{}`'.format(
                command, rc), level=syslog.LOG_WARNING)
        return {'rc': rc, 'out': out, 'err': err}

    def log(self, msg, level=syslog.LOG_DEBUG):
        '''Log to the system logging facility of the target system.''' if os.name == 'posix': # syslog is unsupported on Windows. syslog.syslog(level, str(msg)) 
    def fail(self, msg):
        self._module.fail_json(msg=msg)

    def exit(self, changed=True, msg='', result=None):
        self._module.exit_json(changed=changed, msg=msg, result=result)

    def _parse_params(self, params):
        for param in params:
            if param in self._module.params:
                setattr(self, param, self._module.params[param])
            else:
                setattr(self, param, None)

def chrooted(command, path, profile='/etc/profile', work_dir=None):
    prefix = "chroot {path} bash -c 'source {profile}; ".format(
        path=path, profile=profile)
    if work_dir:
        prefix += 'cd {work_dir}; '.format(work_dir=work_dir)
    prefix += command
    prefix += "'"
    return prefix

# ------------------------------------------------------------------------------
# UNMOUNT POLICIES -------------------------------------------------------------

class BasicUnmounter(BaseObject):
    ''' Unmount all (mounted) partitions.

    Partitions that can't be unmounted are those in use, so the command should
    work correctly (i.e. unmount only partitions of the current setup).
    '''
    def __init__(self, module):
        super(BasicUnmounter, self).__init__(module, params=['basic'])

    def run(self):
        result = []
        mount_points = []

        out = self.run_command('mount')['out']

        for line in out.split(' '):
            md = re.match(r'.+on\s+(\S+).+', line)
            if md:
                mount_point = md.group(1)
                if self.basic and mount_point.startswith(self.basic):
                    mount_points.append(mount_point)

        sort_fn = lambda p: len([e for e in p.split('/') if e])
        mount_points = sorted(mount_points, key=sort_fn, reverse=True)

        for mount_point in mount_points:
            command = 'umount {mount_point}'.format(mount_point=mount_point)
            rc = self.run_command(command, check_rc=False)['rc']
            if rc == 0:
                result.append({'type': 'mount point', 'path': mount_point})

        return result

class LVMUnmounter(BaseObject):
    ''' Unmount all LVM Logical Volumes and Volume Groups.
    '''
    def __init__(self, module):
        super(LVMUnmounter, self).__init__(module)

    def run(self):
        self.run_command('vgchange -a n')
        return [{'type': 'lvm'}]

class EncryptionUnmounter(BaseObject):
    ''' Unmount all Luks volumes.
    '''
    def __init__(self, module):
        super(EncryptionUnmounter, self).__init__(module)

    def run(self):
        result = []

        out = self.run_command('dmsetup info -c -o name')['out']
        lines = [line for line in out.split(' ') if line]
        if len(lines) > 1: # There is at least one device.
            enc_names = map(str.strip, lines[1:])
            for enc_name in enc_names:
                self.run_command('cryptsetup luksClose {}'.format(enc_name))
                result.append({'type': 'encryption', 'name': enc_name})

        return result

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec={
            'basic':      dict(type='str',  default=None),
            'encryption': dict(type='bool', default=False),
            'lvm':        dict(type='bool', default=False),
        })

    unmounted = [] # Informations about unmounted volumes.

    if module.params['basic']:
        unmounted += BasicUnmounter(module).run()

    if module.params['lvm']:
        unmounted += LVMUnmounter(module).run()
        # Maybe some basic partitions can be unmounted now.
        if module.params['basic']:
            unmounted += BasicUnmounter(module).run()

    if module.params['encryption']:
        unmounted += EncryptionUnmounter(module).run()
        # Maybe some basic partitions can be unmounted now.
        if module.params['basic']:
            unmounted += BasicUnmounter(module).run()

    module.exit_json(changed=True, msg='Unmount success', unmounted=unmounted)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
