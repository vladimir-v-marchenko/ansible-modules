#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
---
module: rpm
short_description: Manages packages with the I(rpm) package manager
description:
  - Will install, remove with the I(rpm) package manager.
options:
  name:
    description:
      - ""
    required: true
    default: null
  file:
    description:
      - ""
    required: false
    default: null
  state:
    description:
      - whether to install (C(present)) or remove (C(absent)) a package.
    required: false
    choices: [ "present", "installed", "absent", "removed" ]
    default: "present"
notes: []
requirements: [ rpm ]
author: ITO Nobuaki
'''

EXAMPLES = '''
- rpm: state=installed file=foo.rpm
- rpm: state=removed file=foo.rpm
- rpm: state=removed name=foo
- rpm: state=installed name=failed_if_not_installed
'''

import os
from ansible.module_utils.basic import AnsibleModule

def rpm_install(module, filename):
    file = os.path.expanduser(filename)
    if not os.path.exists(file):
        module.fail_json(msg='No package file: %s' % (filename))

    cmd = [ 'rpm', '-U', '--quiet', file ]
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        return True
    else:
        module.fail_json(msg='Error from rpm: %s: %s' % (cmd, err))

def rpm_erase(module, name):
    cmd = [ 'rpm', '-e', '--quiet', name ]
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        return True
    else:
        module.fail_json(msg='Error from rpm: %s: %s' % (cmd, err))

def rpm_exists(module, name):
    cmd = [ 'rpm', '-q', '--quiet', '--nosignature', name ]
    rc, out, err = module.run_command(cmd)
    return rc == 0

def query_pkgid_for_pkg(module, name):
    cmd = [ 'rpm', '-q', '--qf', '%{PKGID}', '--nosignature',
            name ]
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        return out.strip()
    else:
        return None

def query_rpm_value_for_file(module, filename, format):
    file = os.path.expanduser(filename)
    if not os.path.exists(file):
        module.fail_json(msg='No package file: %s' % (filename))

    cmd = [ 'rpm', '-q', '--qf', format, '--nosignature', '-p', file ]
    rc, out, err = module.run_command(cmd)
    if rc == 0:
        return out
    else:
        module.fail_json(msg='Error from rpm: %s: %s' % (cmd, err))

def query_pkgid_for_file(module, filename):
    return query_rpm_value_for_file(module, filename, '%{PKGID}').strip()

def query_rpm_name_for_file(module, filename):
    return query_rpm_value_for_file(module, filename, '%{NAME}').strip()

def ensure_installed(module, params):
    if params['file']:
        file_pkgid = query_pkgid_for_file(module, params['file'])
        rpm_pkgid  = query_pkgid_for_pkg(module, params['name'])
        if file_pkgid == rpm_pkgid:
            return module.exit_json(changed=False)
        if rpm_install(module, params['file']):
            return module.exit_json(changed=True, name=params['name'],
                                    pkgid=file_pkgid)
    else:
        pkgid = query_pkgid_for_pkg(module, params['name'])
        if pkgid:
            return module.exit_json(changed=False)
        module.fail_json(msg='could not install package %s' % (params['name']))

def ensure_removed(module, params):
    pkgid = query_pkgid_for_pkg(module, params['name'])
    if not pkgid:
        return module.exit_json(changed=False, name=params['name'], pkgid=pkgid)
    if rpm_erase(module, params['name']):
        return module.exit_json(changed=True, name=params['name'], pkgid=pkgid)

def main():
    module = AnsibleModule(
        argument_spec = dict(
            name=dict(),
            state=dict(default='installed', choices=[ 'present', 'absent', 'installed', 'removed' ]),
            file=dict(),
        ),
        required_one_of = [ ['name', 'file'] ]
    )

    params = module.params

    if params['file'] and not params['name']:
        params['name'] = query_rpm_name_for_file(module, params['file'])

    if params['state'] in ['installed', 'present']:
        return ensure_installed(module, params)

    if params['state'] in ['removed', 'absent']:
        return ensure_removed(module, params)

    module.fail_json(msg='Unsupported state' % (params['state']))

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()
