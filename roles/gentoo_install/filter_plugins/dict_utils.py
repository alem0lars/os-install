# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from copy import deepcopy as deep_copy
from ansible.errors import AnsibleFilterError

# ------------------------------------------------------------------------------
# MATCHERS ---------------------------------------------------------------------

def match_key(subject_item, other_item, *key):
    if len(key) == 1:
        subject_key = other_key = key[0]
    elif len(key) == 2:
        subject_key, other_key = key
    else:
        raise AnsibleFilterError('Too many keys to be matched ({} > 2)'.format(
            key))

    return (subject_key in subject_item
        and other_key in other_item
        and subject_item[subject_key] == other_item[other_key])

MATCHERS = {
    'match_key': match_key,
}

# ------------------------------------------------------------------------------
# FILTERS ----------------------------------------------------------------------

def add_item(subject, key, value, condition=True):
    if condition:
        subject[key] = value
    return subject

def map_merge(subject, other, match_fn, *args):
    '''Given two lists of dictionaries, merge the dictionaries.
    Dictionaries are merged if the `match_fn` applied to the single elements,
    returns true.
    Additional arguments are passed to the match function.
    '''

    try:
        match_fn = MATCHERS[match_fn]
    except KeyError:
        raise AnsibleFilterError('Unknown match function')

    subject = list(subject)
    other   = list(other)
    matched = []
    result  = []

    for subject_item in subject:
        for other_item in other:
            if match_fn(subject_item, other_item, *args):
                # Keep track of matched items.
                matched.append(subject_item)
                matched.append(other_item)
                # Compute the resulting item
                # (merging subject item with other item).
                result_item = deep_copy(subject_item)
                result_item.update(other_item)
                result.append(result_item)

    # Add items that never matched, without modifying them.
    for item in subject + other:
        if len(list(filter(lambda m: item is m, matched))) == 0:
            # This item never matched.
            result.append(item)

    return result

# ------------------------------------------------------------------------------
# PLUGIN -----------------------------------------------------------------------

class FilterModule(object):
    '''Ansible jinja2 filters for performing advanced dict-based merges.'''

    def filters(self):
        return {
            'map_merge': map_merge,
            'add_item': add_item,
        }
