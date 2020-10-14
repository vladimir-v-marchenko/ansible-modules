#!/usr/bin/env python

# Change password for a user.

# Note: you must supply both the old and new passwords for this to work

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import os
import platform
import httplib
import urllib
import base64
import json
import string
import random

DOCUMENTATION = '''
---
module: cq_password
short_description: Change Adobe CQ Password
description:
    - Change Adobe CQ Password
author: Paul Markham
notes:
    - This is mostly used to change the Admin password from the default of 'admin'.
options:
    id:
        description:
            - The user ID
        required: true
    old_password:
        description:
            - Old password.
        required: true
    new_password:
        description:
            - New password
        required: true
    host:
        description:
            - Host name where Adobe CQ is running
        required: true
    port:
        description:
            - Port number that Adobe CQ is listening on
        required: true
    ignore_err:
        description:
            - Return ok if neither the old nor new passwords are valid for the user.
        required: false
    version:
        description:
            - version of AEM this module is running against..
        required: false
        default: 6.0.0
'''

EXAMPLES='''
# Change admin password from default
- cq_password: id=admin
              old_password=admin
              new_password=S3cr3t
              host=auth01
              port=4502
'''

from ansible.module_utils.basic import AnsibleModule


# --------------------------------------------------------------------------------
# cq_password class.
# --------------------------------------------------------------------------------
class AEMPassword(object):
    def __init__(self, module):
        self.module            = module
        self.id                = self.module.params['id']
        self.new_password      = self.module.params['new_password']
        self.old_password_list = self.module.params['old_password']
        self.ignore_err        = self.module.params['ignore_err']
        self.host              = self.module.params['host']
        self.port              = self.module.params['port']
        self.version           = self.module.params['version']

        self.changed = False
        self.msg = []
        self.id_initial = self.id[0]

        ver = self.version.split('.')
        if int(ver[0]) >= 6 and int(ver[1]) >= 1:
            self.aem61 = True
        else:
            self.aem61 = False

        self.get_user_info()

    # --------------------------------------------------------------------------------
    # Look up user info.
    # --------------------------------------------------------------------------------

    def get_user_info(self):
        # check if new password is already valid
        self.msg.append('Checking new password')
        if self.aem61:
            (status, output) = self.http_request('GET', '/bin/querybuilder.json?path=/home/users&1_property=rep:authorizableId&1_property.value=%s&p.limit=-1' % (self.id), user = self.id, password = self.new_password)
        else:
            (status, output) = self.http_request('GET', '/home/users/%s/%s.rw.json?props=*' % (self.id_initial, self.id), user = self.id, password = self.new_password)
        if status == 200:
            self.msg.append("password doesn't need to be changed")
            self.exit_status()

        # check if any of the old passwords are valid
        old_password_valid = False
        for password in self.old_password_list:
            self.msg.append('checking password "%s"' % password)
            if self.aem61:
                (status, output) = self.http_request('GET', '/bin/querybuilder.json?path=/home/users&1_property=rep:authorizableId&1_property.value=%s&p.limit=-1' % (self.id), user = self.id, password = password)
            else:
                (status, output) = self.http_request('GET', '/home/users/%s/%s.rw.json?props=*' % (self.id_initial, self.id), user = self.id, password = password)
            if status == 200:
                old_password_valid = True
                self.old_password = password
                break

        if not old_password_valid:
            if self.ignore_err:
                self.msg.append('Ignoring that neither old nor new passwords are valid')
                self.exit_status()
            self.module.fail_json(msg='Neither old nor new passwords are valid')

    # --------------------------------------------------------------------------------
    # Set new password
    # --------------------------------------------------------------------------------
    def set_password(self):
        if not self.module.check_mode:
            if self.aem61:
                fields = [
                    ('plain', self.new_password),
                    ('verify', self.new_password),
                    ('old', self.old_password),
                    ]
                (status, output) = self.http_request('POST', '/crx/explorer/ui/setpassword.jsp', user = self.id, password = self.old_password, fields = fields)
            else:
                fields = [
                    (':currentPassword', self.old_password),
                    ('rep:password', self.new_password),
                    ]
                (status, output) = self.http_request('POST', '/home/users/%s/%s.rw.html' % (self.id_initial, self.id), user = self.id, password = self.old_password, fields = fields)
##            self.exit_status()
            if status != 200:
                self.module.fail_json(msg='failed to change password: %s - %s' % (status, output))
        self.changed = True
        self.msg.append('password changed')

    # --------------------------------------------------------------------------------
    # Issue http request.
    # --------------------------------------------------------------------------------
    def http_request(self, method, url, user, password, fields = None):
        headers = {'Authorization' : 'Basic ' + base64.b64encode(str(user) + ':' + str(password))}
        if fields:
            data = urllib.urlencode(fields)
            headers['Content-type'] = 'application/x-www-form-urlencoded'
        else:
            data = None
        conn = httplib.HTTPConnection(self.host + ':' + str(self.port))
        try:
            conn.request(method, url, data, headers)
        except Exception as e:
            self.module.fail_json(msg="http request '%s %s' failed: %s" % (method, url, e))
        resp = conn.getresponse()
        output = resp.read()
        return (resp.status, output)

    # --------------------------------------------------------------------------------
    # Return status and msg to Ansible.
    # --------------------------------------------------------------------------------
    def exit_status(self):
        msg = ','.join(self.msg)
        self.module.exit_json(changed=self.changed, msg=msg)

# --------------------------------------------------------------------------------
# Mainline.
# --------------------------------------------------------------------------------
def main():
    module = AnsibleModule(
        argument_spec      = dict(
            id             = dict(required=True),
            new_password   = dict(required=True, no_log=True),
            old_password   = dict(required=True, type='list', no_log=True),
            admin_user     = dict(required=False), # no longer needed
            admin_password = dict(required=False, no_log=True), # no longer needed
            host           = dict(default='127.0.0.1'),
            port           = dict(required=True, type='int'),
            ignore_err     = dict(default=True, type='bool'),
            version        = dict(default='6.4.0'),
            ),
        supports_check_mode=True
        )

    password = AEMPassword(module)

    password.set_password()

    password.exit_status()

# --------------------------------------------------------------------------------
# Ansible boiler plate code.
# --------------------------------------------------------------------------------

if __name__ == '__main__':
    main()