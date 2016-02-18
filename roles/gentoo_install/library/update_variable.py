#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from copy import deepcopy

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: update_variable
short_description: Update a variable based on the provided arguments
author:
    - "Alessandro Molari"
'''

EXAMPLES = '''
# Merge the pre-existing user informations with a dictionary of emails
# (e.g.: [{'name': 'Foo', 'email': 'f@o'}, {'name': 'Bar', 'email': 'b@a'}, ..])
- name: Merge user informations
  update_variable:
    subject: "{{ user_info }}"
    with: "{{ emails }}"
    matching: name
  register: user_info
'''

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec={
            'subject': dict(type='list', required=True),
            'with': dict(type='list', required=True),
            'matching': dict(type='str', required=True),
        })

    result = deepcopy(module.params['subject'])
    with_param = deepcopy(module.params['with'])
    key = module.params['matching']

    for result_item in result:
        for with_item in with_param:
            if (key in result_item
                and key in with_param
                and result_item[key] == with_item[key]):
                result_item.update(with_item)

    module.exit_json(changed=True, msg='Variable successfully updated',
                     result=result)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
