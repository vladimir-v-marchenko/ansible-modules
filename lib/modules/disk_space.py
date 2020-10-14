#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stable'],
                    'supported_by': ' "Special DHL-MNT DevOps <SpecialDHL-MNTDevOps@epam.com>"'}


DOCUMENTATION = '''
---
module: disk_space
version_added: 'NA'
short_description: Return disk space stats
description:
    - return disk space stats
options:
  path:
    description:
      - Remote absolute path for get disk space stats. Path will be created if does't exist.
    required: true
  state:
    description:
      - The type of disk space metrics.
    choices: [ 'present', 'used', 'free', 'total' ]
    default: present
author: Volodymyr Marchenko <Volodymyr_Marchenko1@epam.com>
'''

EXAMPLES='''
#####################################################################
# P.S. One Gigabyte = 1073741824 bytes
##
- set_fact:
    download_dir: "/app/downloads"
    empty_space_needed: 1073741824

- name: "Get free space information at /app/downloads"
  disk_space:
    path: "{{ downloads_dir }}"
    state: free
  register: space

- assert:
    fail_msg: "Not enough free disk space in {{ download_dir }} for artifact. Available space: {{ space.result['free'] | int | filesizeformat(True) }}"
    success_msg: "Available free disk space in {{ download_dir }}: {{ space.result['free'] | int | filesizeformat(True) }}"
    that:
      - "{{ empty_space_needed|int <= space.result['free']|int }}"

#####################################################################
##
- name: "Get total disk space of root"
  disk_space:
    state: total
  register: disk_total

#####################################################################
##
- name: "Get disk space stats from path='/' with state='present'"
  disk_space:
  register: disk_stat

'''


RETURN = '''
---
msg: Stats in human readable format
result:
  state: bytes

'''

import os
import sys
import json
import math

from ansible.module_utils.basic import AnsibleModule

def filesizeformat(bytes, precision=2):
    """Returns a humanized string for a given amount of bytes"""
    bytes = int(bytes)
    if bytes is 0:
        return '0bytes'
    log = math.floor(math.log(bytes, 1024))
    return "%.*f%s" % (
        precision,
        bytes / math.pow(1024, log),
        ['bytes', 'kb', 'mb', 'gb', 'tb','pb', 'eb', 'zb', 'yb']
[int(log)]
    )


def disk_usage(path, metric):
    """Return disk usage associated with path."""
    result = {}
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    total = (st.f_blocks * st.f_frsize)
    used = (st.f_blocks - st.f_bfree) * st.f_frsize

    if metric == 'present':
        try:
            percent = (float((st.f_blocks - st.f_bfree) * st.f_frsize) / (st.f_blocks * st.f_frsize)) * 100
        except ZeroDivisionError:
            percent = 0
        result['msg'] = (
            'Free: ' + filesizeformat(free) +
            '\nUsed: ' + filesizeformat(used) +
            '\nTotal: ' + filesizeformat(total) +
            '\nDisk usage: '+ str(round(percent, 1)) + '%'
            )
    elif metric == 'free':
        result['free'] = free
    elif metric == 'total':
        result['total'] = total
    elif metric == 'used':
        result['used'] = used

    return result


def main():
    # load ansible module object
    module = AnsibleModule(
        argument_spec = dict(
            path = dict(required=False, default="/", type=str, aliases=['dest']),
            metric = dict(default='present', choices=[ 'present', 'used', 'free', 'total' ], aliases=['state']),
        ),
        add_file_common_args = False,
        supports_check_mode=True,
    )
    msg = ''
    path = module.params['path']
    metric = module.params['metric']
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            msg = ('Creation of the directory ' + path + ' failed.')
        else:
            msg = ('Successfully created the directory ' + path + '.')

    result = disk_usage(path, metric)
    if metric != 'present':
        msg = msg + 'Disk ' + metric + ': ' +  filesizeformat(result[metric])
        module.exit_json(changed=True, msg=msg, result=result)
    else:
        msg = result['msg']
        module.exit_json(changed=True, msg=msg)




if __name__ == '__main__':
    main()