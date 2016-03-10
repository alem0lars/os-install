# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

from sys import maxsize as max_size

# FILTERS ----------------------------------------------------------------------

def sorted_by_path(subject, attribute=None):
    def sort_fn(elem):
        path = elem
        if attribute is not None:
            attrs = attribute.split('.')
            for attr in attrs:
                if not attr in path:
                    return max_size
                path = path[attr]
        return len([component for component in path.split('/') if component])
    return sorted(subject, key=sort_fn)

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for working with paths.'''

    def filters(self):
        return {'sorted_by_path': sorted_by_path}
