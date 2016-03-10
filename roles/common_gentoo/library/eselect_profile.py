#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import re, sys

PY3K = sys.version_info >= (3, 0)
if PY3K:
    basestring = str

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: eselect
short_description: Perform `eselect` commands
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

# ------------------------------------------------------------------------------
# ESelectProfileExecutor -------------------------------------------------------

class ESelectProfileExecutor(BaseObject):
    def __init__(self, module):
        super(ESelectProfileExecutor, self).__init__(module,
            params=['hardened', 'systemd', 'multilib', 'arch', 'selinux',
                    'desktop', 'developer', 'chroot'])
        self.command_prefix = 'eselect profile'

    def set(self):
        '''Set the profile.
        '''
        profile_regexp = []
        profile_regexp.append(self.hardened or 'default')
        profile_regexp.append('linux')
        profile_regexp.append(self.arch)
        profile_regexp.append('[^/]+')
        if not self.multilib:
            profile_regexp.append('no-multilib')
            if self.hardened and self.selinux:
                profile_regexp.append('selinux')
        elif self.selinux:
            profile_regexp.append('selinux')
        elif self.developer:
            profile_regexp.append('developer')
        elif self.desktop:
            profile_regexp.append(self.desktop)
            if self.systemd:
                profile_regexp.append('systemd')
        elif self.systemd:
            profile_regexp.append('systemd')
        profile_regexp = '/'.join(profile_regexp)

        profile = None
        for prof in self.list():
            if re.match(profile_regexp, prof['name']):
                profile = prof

        if profile is None:
            self.fail('Cannot find a valid profile')

        self.run_command('set {id}'.format(id=profile['id']))

        return profile

    def list(self):
        result = []

        profs = self.run_command('list')['out_lines'][1:]
        profs = map(lambda x: [e for e in re.split(r'\s+', x) if e], profs)
        for prof in profs:
            id_regexp = r'\[(\d+)\]'
            result.append({'id':   int(re.match(id_regexp, prof[0]).group(1)),
                           'name': prof[1]})

        return result

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec={
        'arch': {'type':     'str',
                 'required': True,
                 'choices':  ['alpha', 'amd64', 'arm', 'hppa', 'ia64', 'mips',
                              'ppc', 's390', 'sh', 'sparc', 'x86']},
        'multilib':  {'type': 'bool', 'required': False, 'default': True},
        'hardened':  {'type': 'bool', 'required': False, 'default': False},
        'systemd':   {'type': 'bool', 'required': False, 'default': True},
        'selinux':   {'type': 'bool', 'required': False, 'default': False},
        'developer': {'type': 'bool', 'required': False, 'default': False},
        'desktop':   {'type': 'str',  'required': False, 'default': None},
        'chroot':    {'type': 'str',  'required': False, 'default': None},
    })

    eselect_profile = ESelectProfileExecutor(module)
    profile = eselect_profile.set()
    module.exit_json(changed=True, profile=profile)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
