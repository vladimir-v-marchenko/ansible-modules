#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stableinterface'],
                    'supported_by': 'SpecialDHL-MNTDevOps@epam.com'}

DOCUMENTATION = '''
---
module: get_group
short_description: A wrapper to the unix getent utility
description:
     - Runs getent against one of it's various databases and returns information into
       the host's facts, in a getent_<database> prefixed variable.
author: "Volodymyr Marchenko <volodymyr_marchenko1@epam.com>"
version_added: "1.8"
author:

'''

EXAMPLES = '''

'''
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native


def main():
    module = AnsibleModule(
        argument_spec=dict(
            by_gid=dict(type='str'),
        ),
        supports_check_mode=True,
    )

    colon = ['passwd', 'shadow', 'group', 'gshadow']

    database = 'group'
    key = module.params.get('by_gid')
    split = ':'
    fail_key = True

    getent_bin = module.get_bin_path('getent', True)

    if key is not None:
        cmd = [getent_bin, database, key]
    else:
        cmd = [getent_bin, database]

    try:
        rc, out, err = module.run_command(cmd)
    except Exception as e:
        module.fail_json(msg=to_native(e), exception=traceback.format_exc())

    msg = "Unexpected failure!"
    if database == 'group':
        dbtree = 'ansible_%s_name' % database
    else:
        dbtree = 'getent_%s' % database

    results = {dbtree: {}}

    if rc == 0:
        for line in out.splitlines():
            record = line.split(split)
            results[dbtree] = record[0]

        module.exit_json(ansible_facts=results)

    elif rc == 1:
        msg = "Missing arguments, or database unknown."
    elif rc == 2:
        msg = "One or more supplied key could not be found in the database."
        if not fail_key:
            results[dbtree][key] = None
            module.exit_json(ansible_facts=results, msg=msg)
    elif rc == 3:
        msg = "Enumeration not supported on this database."

    module.fail_json(msg=msg)


if __name__ == '__main__':
    main()
