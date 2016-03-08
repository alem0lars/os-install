#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import sys, re

PY3K = sys.version_info >= (3, 0)

if PY3K:
    from urllib.request import urlopen as url_open
else:
    from urllib import urlopen as url_open

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: select_stage
short_description: Select a Stage.
author:
    - "Alessandro Molari"
'''

EXAMPLES = '''
TODO
'''

# ------------------------------------------------------------------------------
# UTILITIES --------------------------------------------------------------------

def build_regexp(params):
    regexp = ''

    # 1- Date folder.
    regexp += r'\d{8}\/'
    # 2- (Maybe) hardened folder.
    if params['hardened']:
        regexp += r'hardened\/'
    # 3- Architecture file prefix.
    regexp += 'stage3-{arch}'.format(arch=params['arch'])
    # 4- (Maybe) add modifiers to file name.
    modifiers = []
    if params['hardened']:
        modifiers.append('hardened')
    if not params['multilib']:
        modifiers.append('nomultilib')
    if len(modifiers) > 0:
        regexp += '-{modifiers}'.format(modifiers='+'.join(modifiers))
    # 5- Date file suffix.
    regexp += r'-\d{8}'
    # 6- File extension.
    regexp += '.tar.bz2'

    return regexp

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec=dict(
        arch=dict(choices=['alpha', 'amd64', 'arm', 'hppa', 'ia64', 'mips',
                           'ppc', 's390', 'sh', 'sparc', 'x86'],
                  required=True),
        hardened=dict(type='bool', required=True),
        multilib=dict(type='bool', required=True)))

    url = ('http://distfiles.gentoo.org/releases/' +
           '{arch}/'.format(arch=module.params['arch']) +
           'autobuilds/latest-stage3.txt')

    regexp = build_regexp(module.params)

    paths = [line.split(' ')[0] for line in url_open(url).read().splitlines()
             if line and not line.startswith('#')]

    # Find a Stage path matching with provided parameters.
    stage_paths = [path for path in paths if re.match(regexp, path)]

    if len(stage_paths) != 1:
        module.fail_json(msg='Cannot find a matching Stage')

    stage_path = stage_paths[0]

    module.exit_json(changed=True, msg='A Stage archive has been selected.',
                     result=stage_path)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
