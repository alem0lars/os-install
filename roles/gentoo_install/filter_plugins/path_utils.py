#!/usr/bin/python
# -*- coding: utf-8 -*-
# FILTERS ----------------------------------------------------------------------

def sorted_by_path(subject):
    sort_fn = lambda path: len(list(filter(None, path.split('/'))))
    return sorted(subject, key=sort_fn)

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for working with paths.'''

    def filters(self):
        return {
            'sorted_by_path': sorted_by_path,
        }
