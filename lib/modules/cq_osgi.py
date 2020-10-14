#!/usr/bin/env python


from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import os
import platform
import httplib
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
import base64
import json
import yaml

DOCUMENTATION = '''
---
module: cq_osgi
short_description: Manage Adobe CQ osgi settings
description:
    - Create, modify (and delete when implemented) CQ osgi settings
      This module requires pyyaml module to be installed on machine
      running it (this is machine when you run ansible when used as
      local action or target, managed machine when used as regular
      action).
author:

notes:
        - This module manages bolean, string, array, appending to array and factory type settings.
          Deletion (which only makes sense for factory type) is not yet implemented.
            id             = dict(required=True),
            state          = dict(required=True, choices=['present', 'absent']),
            property       = dict(default=None),
            value          = dict(default=None),
            osgimode       = dict(default=None),
            admin_user     = dict(required=True),
            admin_password = dict(required=True),
            host           = dict(required=True),
            port           = dict(required=True),
options:
    id:
        description:
            - The CQ OSGI setting ID
        required: true
    state:
        description:
            - Create or delete the group
        required: true
        choices: [present, absent]
        ABSENT NOT IMPLEMENTED
    property:
        description:
            - Name of the property within specific OSGI id to change. For factory it needs to be just 'factory'
        required: false
    value:
        descritpion:
            - Value to set the property to
    osgimode:
        description:
            mode (type) of osgi property: string, array, arrayappend, factory
    admin_user:
        description:
            - Adobe CQ admin user account name
        required: true
    admin_password:
        description:
            - Adobe CQ admin user account password
        required: true
    host:
        description:
            - Host name where Adobe CQ is running
        required: true
    port:
        description:
            - Port number that Adobe CQ is listening on
        required: true
'''

EXAMPLES='''
# Set/modify a string type setting. Use true or false as value
# to set boolean properties.
  cq_osgi: id=com.some.osgi.id
    property=some.string.type.property
    value="somevalue"
    osgimode=string
    state=present
    admin_user=some_admin_user
    admin_password=some_admin_pass
    host=some_host
    port=some_listen_port

# Create factory type setting
  cq_osgi: id=com.some.osgi.factory.id
    property=factory
    value="{ prop1: value1, prop2: value2, prop3: value3 }"
    osgimode=factory
    state=present
    admin_user=some_admin_user
    admin_password=some_admin_pass
    host=some_host
    port=some_listen_port

# Create factory logger configuration
  cq_osgi: id=com.some.osgi.factory.id
    property=factory
    value="{ 'org.apache.sling.commons.log.level': 'debug',
             'org.apache.sling.commons.log.file': 'logs/standby.log',
             'org.apache.sling.commons.log.pattern': '{0,date,dd.MM.yyyy HH:mm:ss.SSS} *{4}* [{2}] {3} {5}',
             'org.apache.sling.commons.log.names': ['org.apache.jackrabbit.oak.plugins.segment.standby.store.CommunicationObserver'],
           }"
    osgimode=factory
    state=present
    admin_user=some_admin_user
    admin_password=some_admin_pass
    host=some_host
    port=some_listen_port

# Set/modify an array type setting - contents of the property will
# be overwritten by array provided in value
  cq_osgi: id=com.some.osgi.id
    property=some.array.type.property
    value="[ value1, value2 ]"
    osgimode=array
    state=present
    admin_user=some_admin_user
    admin_password=some_admin_pass
    host=some_host
    port=some_listen_port

# Set/modify an array type setting - contents of the property will
# be appended to  array provided in value, idempotently (only once,
# no repeat appending will take place)
  cq_osgi: id=com.some.osgi.id
    property=some.arraytoappendto.type.property
    value="[ value1, value2 ]"
    osgimode=arrayappend
    state=present
    admin_user=some_admin_user
    admin_password=some_admin_pass
    host=some_host
    port=some_listen_port
'''

# --------------------------------------------------------------------------------
# CQOsgi class.
# --------------------------------------------------------------------------------
class CQOsgi(object):
    def __init__(self, module):
        self.module         = module
        self.state          = self.module.params['state']
        self.id             = self.module.params['id']
        self.property       = self.module.params['property']
        self.value          = yaml.load(self.module.params['value'])
        self.osgimode       = self.module.params['osgimode']
        self.admin_user     = self.module.params['admin_user']
        self.admin_password = self.module.params['admin_password']
        self.host           = self.module.params['host']
        self.port           = self.module.params['port']

        self.changed = False
        self.modevalue = { 'string': 'value', 'array': 'values', 'arrayappend': 'values', 'factory': 'na' }
        self.msg = []
        self.factory_instances = []

        self.get_osgi_info()

    # --------------------------------------------------------------------------------
    # Look up package info.
    # --------------------------------------------------------------------------------
    def get_osgi_info(self):
        if self.osgimode in ('string', 'array', 'arrayappend'):
            (status, output) = self.http_request('POST', '/system/console/configMgr/%s' % (self.id))
            info = json.loads(output)
            self.curr_props = info['properties']
            if self.curr_props[self.property]:
                self.exists = True
            else:
                self.exists = False
        elif self.osgimode in ('factory'):
            self.find_factory()
        else:
            self.module.fail_json(msg='osgimode %s not recognized' % self.osgimode)

    # --------------------------------------------------------------------------------
    # Find factory config
    # --------------------------------------------------------------------------------
    def find_factory(self):
        (status, output) = self.http_request('GET', '/system/console/config/Configurations.txt')
        instances = re.findall('^PID.*=.*(%s\.[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})\s*$' % self.id, output, flags=re.M)
        if instances:
            # Instances of a factory found
            factories = {}
            for fi in instances:
                factory_data = re.findall('(PID = %s.*?)\n^PID' % fi, output, flags=re.DOTALL|re.M)
                factory = {}
                for kvp in factory_data[0].splitlines():
                    (k,v) = kvp.strip().split('=')
                    factory[k.strip()] = v.strip()
                factories[fi] = factory
            self.factory_instances = factories
            return True
        else:
            return False

    # --------------------------------------------------------------------------------
    # Check if factory values already match an existing instance
    # --------------------------------------------------------------------------------
    def find_factory_match(self):
        f_match = 0
        factory = ''
        for f, d in self.factory_instances.iteritems():
            v_match = 0
            for k,v in self.value.iteritems():
                if type(v) is int:
                    v = str(v)
                # Lists are returned from Configurations.txt without surrounding quotes
                if type(v) is list:
		    v = str(v).replace("'", "")
                if v == d[k]:
                    v_match += 1
            if v_match == len(self.value.keys()):
                f_match += 1
                factory = f

        if f_match == 0:
            return False
        elif f_match == 1:
            self.factory = factory
            return True
        else:
            self.module.fail_json(msg='Factory %s matches more than one existing factories, this SHOULD not happen' % self.id)

    # --------------------------------------------------------------------------------
    # Create factory config
    # --------------------------------------------------------------------------------
    def create_factory(self):
        fields = []
        if self.module.check_mode:
            return

        fields.append(('apply', 'true'))
        fields.append(('action', 'ajaxConfigManager'))
        fields.append(('factoryPid', self.id))
        for k,v in self.value.iteritems():
            if type(v) is list:
                for vv in v:
                    fields.append((k, vv))
            else:
                fields.append((k, v))
        fields.append(('propertylist', ','.join(self.value.keys())))

        (status, output) = self.http_request2('POST', '/system/console/configMgr/%5BTemporary%20PID%20replaced%20by%20real%20PID%20upon%20save%5D', fields)
        if status != 200:
            self.module.fail_json(msg='failed to create factory %s: %s - %s' % (self.id, status, output))
        self.changed = True
        self.find_factory()
        self.find_factory_match()
        self.msg.append('factory %s created' % (self.factory))

    # --------------------------------------------------------------------------------
    # Delete factory config
    # --------------------------------------------------------------------------------
    def delete_factory(self):
        fields = []
        if self.module.check_mode:
            return

        fields.append(('delete', 'true'))
        fields.append(('apply', 'true'))

        (status, output) = self.http_request2('POST', '/system/console/configMgr/%s' % (self.factory), fields)
        if status != 200:
            self.module.fail_json(msg='failed to delete %s: %s - %s' % (self.factory, status, output))
        self.changed = True
        self.msg.append('factory %s deleted' % (self.factory))

    # --------------------------------------------------------------------------------
    # state='present'
    # --------------------------------------------------------------------------------
    def present(self):

        if self.osgimode in ('factory'):
            if self.factory_instances:
                if self.find_factory_match():
                    self.msg.append('factory %s present' % (self.factory))
                else:
                    self.create_factory()
            else:
                self.create_factory()
        else:
            # For debug
            #self.msg.append('curr_props: %s' % self.curr_props)
            do_update = False
            if type(self.curr_props[self.property][self.modevalue.get(self.osgimode)]) not in (bool, str, unicode):
                #self.module.fail_json(msg='Neither bool nor str: %s' % type(self.curr_props[self.property][self.modevalue.get(self.osgimode)]))
                current = sorted(self.curr_props[self.property][self.modevalue.get(self.osgimode)])
            else:
                current = self.curr_props[self.property][self.modevalue.get(self.osgimode)]

            if self.curr_props[self.property]:
                if self.osgimode == 'arrayappend':
                    combined = sorted(current + self.value)
                    combuniq = sorted(set(combined))
                    self.msg.append('current %s , combined %s , combuniq %s' % (current, combined, combuniq) )
                    if combuniq != current:
                        do_update = True
                elif self.osgimode == 'array' and sorted(current) != sorted(self.value):
                    #self.module.fail_json(msg='current: %s , value: %s' % (current, self.value))
                    do_update = True
                # This encompasses str, unicode and bool, but bool is returned as string, hence casting
                elif self.osgimode == 'string' and  str(current) != str(self.value):
                    do_update = True
            else:
                self.module.fail_json(msg='No such property %s in %s (curr_props: %s)' % (self.property, self.id, self.curr_props))

            if do_update:
                self.update_property()

    # --------------------------------------------------------------------------------
    # state='absent'
    # --------------------------------------------------------------------------------
    def absent(self):
        if self.osgimode in ('factory'):
            if self.factory_instances:
                if self.find_factory_match():
                    self.delete_factory()
                else:
                    self.msg.append('factory already absent')
        else:
            self.module.fail_json(msg='State "absent" is not supported yet, sorry')

    # --------------------------------------------------------------------------------
    # Update property
    # --------------------------------------------------------------------------------
    def update_property(self):
        fields = []
        if self.osgimode not in ['string', 'array', 'arrayappend', 'factory']:
            self.module.fail_json(msg='Currently only string, array, arrayappend and factory modes are supported')
        if not self.module.check_mode:
            fields.append(('apply', 'true'))
            fields.append(('action', 'ajaxConfigManager'))
            if self.osgimode == 'arrayappend':
                for v in self.curr_props[self.property][self.modevalue.get(self.osgimode)]:
                    fields.append((self.property, v))
            if type(self.value) is list:
                for v in self.value:
                    if v not in self.curr_props[self.property]:
                        fields.append((self.property, v))
            else:
                fields.append((self.property, self.value))
            fields.append(('propertylist', self.property))
            (status, output) = self.http_request2('POST', '/system/console/configMgr/%s' % self.id, fields)
            if status != 200:
                self.module.fail_json(msg='failed to update property %s in %s: %s - %s' % (self.property, self.id, status, output))
            self.changed = True
            self.msg.append('property updated')

    # --------------------------------------------------------------------------------
    # Issue http request.
    # --------------------------------------------------------------------------------
    def http_request(self, method, url, fields = None):
        headers = {'Authorization' : 'Basic ' + base64.b64encode(self.admin_user + ':' + self.admin_password)}
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

    def http_request2(self, method, url, fields = None):
        headers = {}
        uri = 'http://' + self.host + ':' + str(self.port) + url
        if fields:
            data = urllib.urlencode(fields)
            headers['Content-type'] = 'application/x-www-form-urlencoded'
        else:
            data = None
        base64string = base64.encodestring('%s:%s' % (self.admin_user, self.admin_password)).replace('\n', '')
        headers['Authorization'] = "Basic %s" % base64string
        request = Request(uri, data, headers)
        try:
            result = urlopen(request)
        except HTTPError as e:
            status = e.code
            output = e.read()
            self.module.fail_json(msg='Request to %s failed with code %s ( output: %s )' % ( uri, status, output ))
        else:
            output = result.read()
            status = result.getcode()
        return (status, output)

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
            state          = dict(required=True, choices=['present', 'absent']),
            property       = dict(default=None),
            value          = dict(default=None, type='str'),
            osgimode       = dict(default=None),
            admin_user     = dict(default='admin', no_log=True),
            admin_password = dict(default='admin', no_log=True),
            host           = dict(default='127.0.0.1'),
            port           = dict(required=True, type='int'),
            ),
        supports_check_mode=True
        )

    osgi = CQOsgi(module)

    state = module.params['state']

    if state == 'present':
        osgi.present()
    elif state == 'absent':
        osgi.absent()
    else:
        module.fail_json(msg='Invalid state: %s' % state)

    osgi.exit_status()

# --------------------------------------------------------------------------------
# Ansible boiler plate code.
# --------------------------------------------------------------------------------

if __name__ == '__main__':
    main()