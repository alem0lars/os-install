#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import glob
import os
import re
import io

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: boot_entry
short_description: Fill a new boot entry
author:
    - "Alessandro Molari"
'''

EXAMPLES = '''
TODO
'''

# ------------------------------------------------------------------------------
# COMMONS (copy&paste) ---------------------------------------------------------

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
        return {'rc': rc,
                'out': out,
                'out_lines': [line for line in out.split('\n') if line],
                'err': err,
                'err_lines': [line for line in out.split('\n') if line]}

    def log(self, msg, level=syslog.LOG_DEBUG):
        '''Log to the system logging facility of the target system.'''
        if os.name == 'posix': # syslog is unsupported on Windows.
            syslog.syslog(level, str(msg))

    def fail(self, msg):
        self._module.fail_json(msg=msg)

    def exit(self, changed=True, msg='', result=None):
        self._module.exit_json(changed=changed, msg=msg, result=result)

    def _parse_params(self, params):
        for param in params:
            if param in self._module.params:
                value = self._module.params[param]
                t = self._module.argument_spec[param].get('type')
                if t == 'str' and value in ['None', 'none']:
                    value = None
                setattr(self, param, value)
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

def find_replace(path, regexp, substitution, append_fallback=False):
    import fileinput, io, os

    found = False

    if os.path.isfile(path):
        for line in fileinput.input(path, inplace=True):
            if re.match(regexp, line):
                found = True
                print(substitution)
            else:
                print(line)

    if not found and append_fallback:
        with io.open(self.loader_conf, 'ab') as f:
            f.write(substitution)

# ------------------------------------------------------------------------------
# BOOT ENTRIES -----------------------------------------------------------------

class BootEntry(BaseObject):
    def __init__(self, module):
        super(BootEntry, self).__init__(module,
            params=['name', 'title', 'kind', 'default', 'base_dir', 'chroot',
                    'vmlinuz', 'initrd', 'root_dev', 'enc_name'])

        uname = self.run_command('uname -r')['out_lines'][0]

        if self.vmlinuz is None:
            self.vmlinuz = r'vmlinuz-{uname}'.format(uname=uname)

        if self.initrd is None:
            self.initrd = r'initrd-{uname}'.format(uname=uname)

        if not self.title:
            self.title = self.vmlinuz

        self.entry_conf = os.path.join(self.base_dir, 'loader', 'entries',
                                       '{name}.conf'.format(name=self.name))

        self.loader_conf = os.path.join(self.base_dir, 'loader', 'loader.conf')

        if self.root_dev is None:

            devices = filter(lambda line: re.match(r'.+on / type', line),
                             self.run_command('mount')['out_lines'])
            if len(devices) != 1:
                self.fail('Internal error in `boot_entry`')
            self.root_dev = devices[0].split(' ')[0]

        if (self.enc_name and
            self.run_command('blkid -t UUID={}'.format(self.enc_name),
                             check_rc=False)['rc'] != 0):
            cmd = 'blkid -t PARTLABEL={} -s UUID -o value'.format(self.enc_name)
            self.enc_name = self.run_command(cmd)['out_lines'][0]

        self.options = []
        if self.enc_name:
            self.options.append('rd.luks.uuid={}'.format(self.enc_name))
        self.options.append('init=/usr/lib/systemd/systemd')
        self.options.append('root={device}'.format(device=self.root_dev))
        self.options.append('rw')

    def run(self):
        if not os.path.isdir(os.path.dirname(self.entry_conf)):
            self.run_command('mkdir -p {}'.format(
                os.path.dirname(self.entry_conf)))

        with io.open(self.chroot + self.entry_conf, 'wb') as f:
            f.write('\n'.join([
                'title   {}'.format(self.title),
                'linux   {}'.format(os.path.join('/', self.vmlinuz)),
                'initrd  {}'.format(os.path.join('/', self.initrd)),
                'options {}'.format(' '.join(self.options)),
                ]) + '\n')

        if self.default:
            find_replace(self.chroot + self.loader_conf,
                         r'default\s+(\S+)',
                         'default {name}'.format(name=self.name),
                         append_fallback=True)

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec={
        'name':     {'type': 'str',  'required': True},
        'title':    {'type': 'str',  'required': False, 'default': None},
        'vmlinuz':  {'type': 'str',  'required': False, 'default': None},
        'initrd':   {'type': 'str',  'required': False, 'default': None},
        'enc_name': {'type': 'str',  'required': False, 'default': None},
        'root_dev': {'type': 'str',  'required': False, 'default': None},
        'default':  {'type': 'bool', 'required': False, 'default': False},
        'base_dir': {'type': 'str',  'required': True},
        'chroot':   {'type': 'str',  'required': False, 'default': None},
        })

    boot_entry = BootEntry(module)

    boot_entry.run()

    module.exit_json(changed=True, msg='Boot entry successfully added')

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
