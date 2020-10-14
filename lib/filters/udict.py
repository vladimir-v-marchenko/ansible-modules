# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


import itertools
from ansible import errors
import sys


def udict(*terms, **kwargs):
    for t in terms:
        if not isinstance(t, dict):
            raise errors.AnsibleFilterError("|udict expects dictionaries, got " + repr(t))

    d = terms[0]
    # Extract the dictionary into a list of (key, value) tuples.
    term_keys = [(k, d[k]) for k in d]
    term_keys.sort()
    d = {}

    for k, v in term_keys:
        if v in d.values():
            continue
        d[k] = v

    return d


class FilterModule(object):
    ''' Ansible core jinja2 filters '''

    def filters(self):
        return {
            'udict': udict,
        }
