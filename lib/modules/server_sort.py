#!/usr/bin/env python
# Copyright 2014, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DOCUMENTATION = """
---
module: dist_sort
version_added: "1.6.6"
short_description:
   - Deterministically sort a list to distribute the elements in the list
     evenly. Based on external values such as host or static modifier. Returns
     a string as named key ``sorted_list``.
description:
   - This module returns a list of servers uniquely sorted based on a index
     from a look up value location within a group. The group should be an
     existing ansible inventory group. This will module returns the sorted
     list as a delimited string.
options:
    src_list:
        description:
            - list in the form of a string separated by a delimiter.
        required: True
    ref_list:
        description:
            - list to lookup value_to_lookup against to return index number
              This should be a pre-determined ansible group containing the
              ``value_to_lookup``.
        required: False
    value_to_lookup:
        description:
            - value is looked up against ref_list to get index number.
        required: False
    sort_modifier:
        description:
            - add a static int into the sort equation to weight the output.
        type: int
        default: 0
    delimiter:
        description:
            - delimiter used to parse ``src_list`` with.
        default: ','
author: Sam Yaple
"""

EXAMPLES = """
- dist_sort:
    value_to_lookup: "Hostname-in-ansible-group_name"
    ref_list: "{{ groups['group_name'] }}"
    src_list: "Server1,Server2,Server3"
  register: test_var

# With a pre-set delimiter
- dist_sort:
    value_to_lookup: "Hostname-in-ansible-group_name"
    ref_list: "{{ groups['group_name'] }}"
    src_list: "Server1|Server2|Server3"
    delimiter: '|'
  register: test_var

# With a set modifier
- dist_sort:
    value_to_lookup: "Hostname-in-ansible-group_name"
    ref_list: "{{ groups['group_name'] }}"
    src_list: "Server1#Server2#Server3"
    delimiter: '#'
    sort_modifier: 5
  register: test_var
"""


class DistSort(object):
    def __init__(self, module):
        """Deterministically sort a list of servers.

        :param module: The active ansible module.
        :type module: ``class``
        """
        self.module = module
        self.params = self.module.params
        self.return_data = self._runner()

    def _runner(self):
        """Return the sorted list of servers.

        Based on the modulo of index of a *value_to_lookup* from an ansible
        group this function will return a comma "delimiter" separated list of
        items.

        :returns: ``str``
        """
        index = self.params['ref_list'].index(self.params['value_to_lookup'])
        index += self.params['sort_modifier']
        src_list = self.params['src_list'].split(
            self.params['delimiter']
        )

        for _ in range(index % len(src_list)):
            src_list.append(src_list.pop(0))
        else:
            return self.params['delimiter'].join(src_list)


def main():
    """Run the main app."""
    module = AnsibleModule(
        argument_spec=dict(
            value_to_lookup=dict(
                required=True,
                type='str'
            ),
            ref_list=dict(
                required=True,
                type='list'
            ),
            src_list=dict(
                required=True,
                type='str'
            ),
            delimiter=dict(
                required=False,
                type='str',
                default=','
            ),
            sort_modifier=dict(
                required=False,
                type='str',
                default='0'
            )
        ),
        supports_check_mode=False
    )
    try:
        # This is done so that the failure can be parsed and does not cause
        # ansible to fail if a non-int is passed.
        module.params['sort_modifier'] = int(module.params['sort_modifier'])

        _ds = DistSort(module=module)
        if _ds.return_data == module.params['src_list']:
            _changed = False
        else:
            _changed = True

        module.exit_json(changed=_changed, **{'sorted_list': _ds.return_data})
    except Exception as exp:
        resp = {'stderr': str(exp)}
        resp.update(module.params)
        module.fail_json(msg='Failed Process', **resp)

# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
