#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import os

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: kernel_config
short_description: Configure the Linux kernel with provided options
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
                t = self._module.argument_spec[param].get('type')
                if t == 'str' and param in ['None', 'none']:
                    param = None
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
# CONFIGURATOR -----------------------------------------------------------------

class KernelOptionConfigurator(BaseObject):
    '''Manipulate options in a kernel config file.
    '''
    def __init__(self, module):
        super(KernelOptionConfigurator, self).__init__(module,
            params=['as_module', 'value', 'kind', 'after'])
        self.kernel_option = KernelOption(module)

    def run(self):
        if self.value == True:
            self.kernel_option.enable()
        elif self.value == False:
            self.kernel_option.disable()
        elif self.value in ['undef', 'undefined']:
            self.kernel_option.undefine()
        else:
            self.kernel_option.set_value()

        if self.as_module:
            self.kernel_option.as_module()

class KernelOption(BaseObject):
    '''Represent a kernel option and the related operations.
    '''
    def __init__(self, module):
        super(KernelOption, self).__init__(module,
            params=['kernel_dir', 'option', 'value', 'kind', 'after'])
        self.command_prefix = '{cmd} --file {kernel_dir}'.format(
            cmd=os.path.join(self.kernel_dir, 'scripts', 'config'),
            kernel_dir=os.path.join(self.kernel_dir, '.config'))

    def enable(self):
        '''Enable a kernel option.
        '''
        self.run_command('--enable {option}'.format(option=self.option))
        if self.after:
            self.run_command('--enable-after {after} {option}'.format(
                             after=self.after, option=self.option))

    def disable(self):
        '''Disable a kernel option.
        '''
        self.run_command('--disable {option}'.format(option=self.option))
        if self.after:
            self.run_command('--disable-after {after} {option}'.format(
                             after=self.after, option=self.option))

    def as_module(self):
        '''Turn a option into a module.
        '''
        self.run_command('--module {option}'.format(option=self.option))
        if self.after:
            self.run_command('--module-after {after} {option}'.format(
                             after=self.after, option=self.option))

    def undefine(self):
        self.run_command('--undefine {option}'.format(option=self.option))

    def set_value(self):
        '''Set option to the provided value.
        Kind indicates:
        - `value`: `value` is a value.
        - `string`: `value` is a string.
        - `undefined`: the option should be unset.
        '''
        if self.value is None:
            self.fail('Invalid `value`: it cannot be `None`')
        if self.kind in ['str', 'string']:
            self.run_command('--set-str {option} {value}'.format(
                option=self.option, value=self.value))
        elif self.kind == 'value':
            self.run_command('--set-val {option} {value}'.format(
                option=self.option, value=self.value))
        else:
            self.fail('Invalid `kind`: it cannot be `None`')

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec=dict(
        kernel_dir=dict(type='str', default='/usr/src/linux'),
        option=dict(type='str', required=True),
        value=dict(default=True),
        as_module=dict(type='bool', default=False),
        kind=dict(type='str', default=None),
        after=dict(type='str', default=None)))

    configurator = KernelOptionConfigurator(module)

    configurator.run()

    module.exit_json(changed=True,
                     msg='Kernel option {name} successfully configured'.format(
                         name=module.params['option']))

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
