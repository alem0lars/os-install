#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from sys import version_info as py_version_info

PY3K = py_version_info >= (3, 0)
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
# ESelect ----------------------------------------------------------------------

class ESelectExecutor(BaseObject):

    def __init__(self, module, subject, value):
        super(ESelectExecutor, self).__init__(module, params=['action'])
        self.command_prefix = 'eselect'
        self.subject = subject
        self.value   = value

    def run(self):
        if self.action == 'set':
            self.set()
        else:
            self.fail('Invalid action: {}'.format(action=self.action))

    @classmethod
    def create(cls, module):
        executors = []
        for subject, value in module.params['values']:
            if subject == 'profile':
                executor = ESelectProfileExecutor(module, subject, value)
            else:
                executor = GenericProfileExecutor(module, subject, value)
            executors.append(executor)
        return executors

class ESelectProfileExecutor(ESelectExecutor):
    def __init__(self, module, subject, value):
        super(ESelectProfileExecutor, self).__init__(module, subject, value)

    def set(self):
        profile_id = None # TODO
        self.run_command('profile set {id}'.format(id=profile_id))

class GenericProfileExecutor(ESelectExecutor):
    def __init__(self, module):
        super(GenericProfileExecutor, self).__init__(module, subject, value)

    def set(self):
        self.run_command('{subject} set {value}'.format(
            subject=self.subject, value=self.value))

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec={
            'action': dict(choices=['set'], required=True),
            'values': dict(type='dict', default={})
        })

    executors = ESelectExecutor.create(module)

    messages = [executor.run() for executor in executors]

    module.exit_json(changed=True, messages=messages)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
