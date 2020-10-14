#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stable'],
                    'supported_by': ' "Special DHL-MNT DevOps <SpecialDHL-MNTDevOps@epam.com>"'}



import os
import sys
import shutil
import json

from ansible.module_utils.basic import AnsibleModule


# def check_path(path):

def main():
    # load ansible module object
    module = AnsibleModule(
        argument_spec = dict(
            src = dict(required=True, type='path', aliases=['path']),
            dest =  dict(required=True, type='path'),
            force = dict(required=False, default=False, type='bool'),
            # state = dict(default='moved', choices=[ 'moved', 'used', 'free', 'total' ], aliases=['state']),
        ),
        add_file_common_args = True,
        supports_check_mode=True,
    )
    # dir_mode = False
    # file_mode = False
    src = module.params['src']
    dest = module.params['dest']
    force = module.params['force']

    if not os.path.exists(src):
        module.fail_json(changed=False, msg="Path src=%s is not exist" % (src))
    elif src == dest:
        module.fail_json(changed=False, msg="Can't move src=%s to dest=%s" % (src, dest))
    elif os.path.exists(dest):
        module.fail_json(changed=False, msg="Path: dest=%s is already exist" % (dest))

    try:
        result = shutil.move(src, dest)
        if not os.path.exists(src) and os.path.exists(dest):
            module.exit_json(changed=True, src=src, dest=dest, force=force, result=result)
        elif os.path.exists(src) and not os.path.exists(dest):
            module.fail_json(changed=False, src=src, dest=dest, force=force, result=result, msg="Failed move src=%s to dest=%s" % (src, dest))
        elif not os.path.exists(src) and not os.path.exists(dest):
            module.fail_json(changed=False, src=src, dest=dest, force=force, result=result, msg="Paths not exists: src=%s and dest=%s " % (src, dest))
        else:
            module.fail_json(changed=False, src=src, dest=dest, force=force, result=result, msg="Failed move src=%s to dest=%s" % (src, dest))
    except OSError:
        module.fail_json(changed=False, src=src, dest=dest, force=force, result=result, msg='Moving src=%s to dest=%s faled' % (src, dest))


# import module snippets
if __name__ == '__main__':
    main()