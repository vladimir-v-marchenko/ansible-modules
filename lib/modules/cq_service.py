#!/usr/bin/python

import sys
import os
import platform
import httplib
import urllib
import base64
import json
import socket
import re
import time

DOCUMENTATION = '''
---
module: cq_service
short_description: Manage AEM Instances
description:
    - Start and stop CQ AEM instances
author:
notes:
        - When starting a AEM instance, this module waits for it to be fully up before returning. It does this by retrieving the
          specified URI and searching for a matching pattern. Author and publish instances may need a different URI specified
          if the default login page has been changed. Note that the page checked must be retrievable without having to login to
          AEM.
options:
    state:
        description:
            - Stop or start the instance
        required: true
        choices: [started, stopped]
    uri:
        description:
            - The URI of the page to fetch to check if AEM has started.
              Only required when starting AEM.
        required: false
    pattern:
        description:
            - The pattern to look for in the retrieved URI to check if AEM has started.
              Only required when starting AEM.
        required: false
    cmd:
        description:
            - The command used to start or stop AEM.
        required: false
        default: service adobecq start, service adobecq stop
    host:
        description:
            - Host name where AEM is running
        required: true
    port:
        description:
            - Port number that AEM is listening on
        required: true
    admin_user:
        description:
            - The admin username - normally admin
              Only required when starting AEM author standby.
        required: false
    admin_password:
        description:
            - The admin password
              Only required when starting AEM author standby.
        required: false
    authenticate:
        description:
            - Whether to use user+password authentication to retrieve the URI.
        required: false
    timeout:
        description:
            - Maximum time, in seconds, to wait for AEM to start or stop. The module exits with an error if this is exceeded.
        required: false
        default: 600
'''

EXAMPLES='''
# Start AEM
- cq_service: state=started
             uri='/libs/granite/core/content/login.html'
             pattern='<title>AEM Sign In</title>'
             host=auth01
             port=4502

# Stop AEM
- cq_service: state=stopped
             host=auth01
             port=4502
'''

# --------------------------------------------------------------------------------
# cq_service class.
# --------------------------------------------------------------------------------
class cq_service(object):
    def __init__(self, module):
        self.module         = module
        self.state          = self.module.params['state']
        self.uri            = self.module.params['uri']
        self.pattern        = self.module.params['pattern']
        self.cmd            = self.module.params['cmd']
        self.host           = self.module.params['host']
        self.port           = self.module.params['port']
        self.admin_user     = self.module.params['admin_user']
        self.admin_password = self.module.params['admin_password']
        self.timeout        = self.module.params['timeout']
        self.verbose        = self.module.params['verbose']
        self.authenticate   = self.module.params['authenticate']

        self.changed = False
        self.msg = []
        self.auth_done = False

        self.process_running = self.get_process_state()

    # --------------------------------------------------------------------------------
    # Determine if the process is running. AEM opens its socket early in its startup,
    # so use this to determine if the process is running, even if it's not fully up yet.
    # --------------------------------------------------------------------------------
    def get_process_state(self):
        s = socket.socket()
        result = s.connect_ex((self.host, int(self.port)))
        s.close()
        if result == 0:
            if self.verbose:
                self.msg.append('port is open')
            return True
        else:
            if self.verbose:
                self.msg.append('port is closed')
            return False

    # --------------------------------------------------------------------------------
    # Wait for the AEM instance to be fully started. Do this by getting the URI
    # and checking if the response contains the pattern. If not, sleep for a while
    # and try again.
    # --------------------------------------------------------------------------------
    def wait_for_active_instance(self):
        start_time = time.time()
        while True:
            url = 'http://%s:%d%s' % (self.host, self.port, self.uri)
            try:
                (resp, output) = self.http_request('GET', url)
                result = re.search(self.pattern, output)
            except:
                result = None
            if result:
                if self.verbose:
                    self.msg.append('Instance is active')
                break
            if time.time() - start_time > self.timeout:
                self.module.fail_json(msg='Timed out waiting for instance to become active')
            time.sleep(10)
            continue

    # --------------------------------------------------------------------------------
    # state='started'
    # --------------------------------------------------------------------------------
    def started(self):
        if not self.pattern:
            self.module.fail_json(msg='missing required arguments: pattern')
        if not self.uri:
            self.module.fail_json(msg='missing required arguments: uri')
        if self.process_running:
            self.wait_for_active_instance()
        else:
            if not self.module.check_mode:
                self.start_aem()
            self.changed = True
            self.msg.append('Service cq started')

    # --------------------------------------------------------------------------------
    # state='stopped'
    # --------------------------------------------------------------------------------
    def stopped(self):
        if self.process_running:
            if not self.module.check_mode:
                self.stop_aem()
            self.changed = True
            self.msg.append('Service cq stopped')

    # --------------------------------------------------------------------------------
    # Start AEM
    # --------------------------------------------------------------------------------
    def start_aem(self):
        if self.cmd == None:
            self.cmd = "Service cq start"
        (rc, out, err) = self.module.run_command(self.cmd)
        if rc != 0:
            self.module.fail_json(msg='Error running command "%s"' % self.cmd)
        start_time = time.time()
        while True:
            running = self.get_process_state()
            if running:
                break
            if time.time() - start_time > self.timeout:
                self.module.fail_json(msg='Timed out waiting for instance to start')
            time.sleep(10)
            continue
        self.wait_for_active_instance()

    # --------------------------------------------------------------------------------
    # Stop AEM
    # --------------------------------------------------------------------------------
    def stop_aem(self):
        if self.cmd == None:
            self.cmd = "service cq stop"
        (rc, out, err) = self.module.run_command(self.cmd)
        if rc != 0:
            self.module.fail_json(msg='Error running command "%s"' % self.cmd)
        start_time = time.time()
        while True:
            running = self.get_process_state()
            if not running:
                break
            if time.time() - start_time > self.timeout:
                self.module.fail_json(msg='Timed out waiting for instance to stop')
            time.sleep(10)
            continue
        # Give instance a chance to fully stop after TCP port is closed.
        time.sleep(10)

    # --------------------------------------------------------------------------------
    # Issue http request.
    # --------------------------------------------------------------------------------
    def http_request(self, method, url):
        if self.authenticate and self.admin_user and self.admin_password:
            if self.auth_done is not True:
                self.msg.append('authentication used')
                self.auth_done = True
            headers = {'Authorization' : 'Basic ' + base64.b64encode(self.admin_user + ':' + self.admin_password)}
        else:
            headers = {}

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
        msg = ', '.join(self.msg)
        self.module.exit_json(changed=self.changed, msg=msg)


# --------------------------------------------------------------------------------
# Mainline.
# --------------------------------------------------------------------------------
def main():
    module = AnsibleModule(
        argument_spec      = dict(
            state          = dict(required=True, choices=['started', 'stopped']),
            uri            = dict(required=False, default='/libs/granite/core/content/login.html'),
            pattern        = dict(default='<title>AEM Sign In</title>'),
            cmd            = dict(default=None),
            verbose        = dict(default=False, type='bool'),
            host           = dict(default='127.0.0.1'),
            port           = dict(required=True, type='int'),
            admin_user     = dict(required=False),
            admin_password = dict(required=False, no_log=True),
            timeout        = dict(default=600, type='int'),
            authenticate   = dict(default=False, type='bool'),
            ),
        supports_check_mode=True
        )

    service = cq_service(module)

    state = module.params['state']

    if state == 'started':
        service.started()
    elif state == 'stopped':
        service.stopped()
    else:
        module.fail_json(msg='Invalid state: %s' % state)

    service.exit_status()

# --------------------------------------------------------------------------------
# Ansible boiler plate code.
# --------------------------------------------------------------------------------
from ansible.module_utils.basic import *
main()
