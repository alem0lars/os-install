# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

from sys import maxsize as max_size

# FILTERS ----------------------------------------------------------------------

def sorted_by_path(subject, attribute=None):
    def sort_fn(elem):
        if attribute is not None:
            if attribute in elem:
                path = elem[attribute]
            else:
                return max_size
        else: # By default, consider the subject as a list of strings (paths).
            path = elem
        return len([component for component in path.split('/') if component])
    return sorted(subject, key=sort_fn)

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for working with paths.'''

    def filters(self):
        return {'sorted_by_path': sorted_by_path}
