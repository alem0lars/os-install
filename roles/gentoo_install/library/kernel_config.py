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

#    commands:
#            --enable-after|-E beforeopt option
#                                 Enable option directly after other option
#            --disable-after|-D beforeopt option
#                                 Disable option directly after other option
#            --module-after|-M beforeopt option
#                                 Turn option into module directly after other option
#    
#            commands can be repeated multiple times
#    
#    options:
#            --file config-file   .config file to change (default .config)
#            --keep-case|-k       Keep next symbols' case (dont' upper-case it)

# ------------------------------------------------------------------------------
# COMMONS (generated) ----------------------------------------------------------

class BaseObject(object):
    import syslog, os

    '''Base class for all classes that use AnsibleModule.
    '''
    def __init__(self, module, *params):
        syslog.openlog('ansible-{module}-{name}'.format(
            module=os.path.basename(__file__), name=self.__class__.__name__))
        self._module = module
        self._parse_params(*params)

    def run_command(self, *args, **kwargs):
        if not 'check_rc' in kwargs:
            kwargs['check_rc'] = True
        if len(args) < 1:
            self.fail('Invalid command')
        self.log('Performing command `{}`'.format(args[0]))
        rc, out, err = self._module.run_command(*args, **kwargs)
        if rc != 0:
            self.log('Command `{}` returned invalid status code: `{}`'.format(
                args[0], rc), level=syslog.LOG_WARNING)
        return {'rc': rc, 'out': out, 'err': err}

    def log(self, msg, level=syslog.LOG_DEBUG):
        '''Log to the system logging facility of the target system.'''
        if os.name == 'posix': # syslog is unsupported on Windows.
            syslog.syslog(level, str(msg))

    def fail(self, msg):
        self._module.fail_json(msg=msg)

    def exit(self, changed=True, msg='', result=None):
        self._module.exit_json(changed=changed, msg=msg, result=result)

    def _parse_params(self, *params):
        for param in params:
            if param in self._module.params:
                setattr(self, param, self._module.params[param])
            else:
                setattr(self, param, None)

# ------------------------------------------------------------------------------
# CONFIGURATOR -----------------------------------------------------------------

class KernelConfigurator(BaseObject):
    '''Manipulate options in a kernel config file.
    '''
    def __init__(self, module):
        super(KernelConfigurator, self).__init__(module, 'kernel_dir')
        self._config_path = os.path.join(self.kernel_dir, '.config')
        self._script_path = os.path.join(self.kernel_dir, 'scripts', 'config')

    def enable(option_name):
        '''Enable a kernel option.
        '''
        self.run_command('{cmd} --enable {option_name}'.format(
            cmd=self._script_path, option_name=option_name))

    def disable(option_name):
        '''Disable a kernel option.
        '''
        self.run_command('{cmd} --disable {option}'.format(
            cmd=self._script_path, option=option_name))

    def as_module(option_name):
        '''Turn a option into a module.
        '''
        self.run_command('{cmd} --module {option}'.format(
            cmd=self._script_path, option=option_name))

    def set_value(kind, option_name, option_value=None):
        '''Set option to the provided value.
        Kind indicates:
        - `value`: `option_value` is a string.
        - `string`: `option_value` is a string.
        - `undefined`: the option should be unset.
        '''
        if kind in ['undef', 'undefined']:
            self.run_command('{cmd} --undefine {option}'.format(
                cmd=self._script_path, option=option_name))
        elif kind in ['str', 'string']:
            self.run_command('{cmd} --set-str {option} {value}'.format(
                cmd=self._script_path, option=option_name, value=option_value))
        elif kind == 'value':
            self.run_command('{cmd} --set-val {option} {value}'.format(
                cmd=self._script_path, option=option_name, value=option_value))

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec=dict(
        kernel_dir=dict(type='str', default='/usr/src/linux'),
        option=dict(type='str', required=True),
        as_module=dict(type='bool', required=True),
        value=dict(type='str', required=True),
        kind=dict(type='str', default=None),
        after=dict(type='list', default=[])))

    configurator = KernelConfigurator(module)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
