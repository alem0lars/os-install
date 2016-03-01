#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from os.path import join as join_path

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
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec=dict(
        kernel_dir=dict(type='str', default='/usr/src/linux'),
        option=dict(type='str', required=True),
        as_module=dict(type='bool', required=True),
        value=dict(type='str', required=True),
        kind=dict(type='str', default=None),
        after=dict(type='list', default=[])))

    fail_handler = lambda msg: module.fail_json(msg=msg)
    cmd_runner   = lambda *args, **kwargs: module.run_command(*args, **kwargs)

class KernelConfigurator(object):
    def __init__(self, kernel_dir, cmd_runner, fail_handler):
        self._kernel_dir = kernel_dir
        self._config_path = join_path(self._kernel_dir, '.config')
        self._script_path = join_path(self._kernel_dir, 'scripts', 'config')
        self._cmd_runner = cmd_runner
        self._fail_handler = fail_handler

    def enable(option_name):
        self._cmd_runner('{cmd} --enable {option_name}'.format(
            cmd=self._script_path, option_name=option_name))

    def disable(option_name):
        self._cmd_runner('{cmd} --disable {option}'.format(
            cmd=self._script_path, option=option_name))

    def as_module(option_name):
        self._cmd_runner('{cmd} --module {option}'.format(
            cmd=self._script_path, option=option_name))

    def set_value(option_name, option_value, kind):
        if kind is None:
            if option_value in ['undef', 'undefined']:
                self._cmd_runner('{cmd} --undefine {option}'.format(
                    cmd=self._script_path, option=option_name))
            else:
                self._fail_handler('Unknown option kind')
        elif kind in ['str', 'string']:
            # TODO
            pass
        elif kind == 'value':
            # TODO
            pass


    # TODO
    #option:    "{{ item.name }}"
    #as_module: "{{ item.as_module | default(false) }}"
    #value:     "{{ item.value }}"
    #type:      "{{ item.type | default(omit) }}"
    #after:     "{{ item.enable_after | default(omit) }}"
    #
    #$ ./scripts/config --help
    #Manipulate options in a .config file from the command line.
    #Usage:
    #config options command ...
    #commands:
    #        --enable|-e option   Enable option
    #        --disable|-d option  Disable option
    #        --module|-m option   Turn option into a module
    #        --set-str option string
    #                             Set option to "string"
    #        --set-val option value
    #                             Set option to value
    #        --undefine|-u option Undefine option
    #        --state|-s option    Print state of option (n,y,m,undef)
    #
    #        --enable-after|-E beforeopt option
    #                             Enable option directly after other option
    #        --disable-after|-D beforeopt option
    #                             Disable option directly after other option
    #        --module-after|-M beforeopt option
    #                             Turn option into module directly after other option
    #
    #        commands can be repeated multiple times
    #
    #options:
    #        --file config-file   .config file to change (default .config)
    #        --keep-case|-k       Keep next symbols' case (dont' upper-case it)
    #
    #config doesn't check the validity of the .config file. This is done at next
    #make time.
    #
    #By default, config will upper-case the given symbol. Use --keep-case to keep
    #the case of all following symbols unchanged.
    #
    #config uses 'CONFIG_' as the default symbol prefix. Set the environment
    #variable CONFIG_ to the prefix to use. Eg.: CONFIG_="FOO_" config ...

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
