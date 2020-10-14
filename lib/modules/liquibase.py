#!/usr/bin/python

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: liquibase

short_description: This is my test module

version_added: "2.4"

description:
    - "This is my longer description explaining my test module"

options:
    name:
        description:
            - This is the message to send to the test module
        required: true
    new:
        description:
            - Control to demo if the result of this module is changed or not
        required: false

author:
    - Your Name (@yourhandle)
'''

EXAMPLES = '''
# Pass in a message
- name: Test with a message
  my_test:
    name: hello world

# pass in a message and have changed true
- name: Test with a message and changed output
  my_test:
    name: hello world
    new: true

# fail the module
- name: Test failure of the module
  my_test:
    name: fail me
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
    returned: always
message:
    description: The output message that the test module generates
    type: str
    returned: always
'''
import sys, os, fnmatch

from ansible.module_utils.basic import AnsibleModule

def run_commands(module, cmd, check_rc=True):
    return module.run_command(cmd, check_rc)

def return_last(data):
    if isinstance(data, list):
        return data[-1]
    elif isinstance(data, str) and data != '':
        return data

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        liquibase_home     = dict(type='path', required=False),
        schemas_dir        = dict(type='path', required=True),
        driver             = dict(type='str', default='oracle.jdbc.OracleDriver', required=False),
        classpath          = dict(type='str', required=False),
        contexts           = dict(type='str', required=False),
        parameters         = dict(type='str', required=False),
        java_parameters    = dict(type='str', required=False),
        changeLogFile      = dict(type='str', default='db.changelog-master.xml', aliases=['changelog','changelog_file'], required=False),
        defaultsFile       = dict(type='str', default='liquibase.properties', aliases=['defaults', 'defaults_file', 'liquibase_properties'], required=False),
        command            = dict(type='str', choices=['releaseLocks', 'clearCheckSums', 'update', 'dropAll'], required=True, aliases=['state']),
        username           = dict(type='str', aliases=['user','ora_user'], required=True),
        password           = dict(type='str', aliases=['ora_password'], required=True, no_log=True),
        hostname           = dict(type='str', aliases=['host', 'ora_host'], required=True),
        port               = dict(type='int', default=1521, aliases=['ora_port'], required=False),
        service_name       = dict(type='str', aliases=['ora_sid', 'sid', 'ora_service', 'sn', 'service'], required=True),
        print_log          = dict(type='bool', default=False, required=False),
        logLevel           = dict(type='str', choices=[ 'debug', 'info', 'warning' ], aliases=['loglevel'], default='debug'),
        logFile            = dict(type='str', default='liquibase.log', aliases=['logfile'], required=False)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    paths = []

    if module.params['liquibase_home'] and os.path.exists(module.params['liquibase_home']):
        liquibase_home = module.params['liquibase_home']
        os.environ['LIQUIBASE_HOME'] = liquibase_home
    elif os.getenv('LIQUIBASE_HOME') and os.path.exists(os.getenv('LIQUIBASE_HOME')):
        liquibase_home = os.environ.get('LIQUIBASE_HOME')
    else:
        msg = 'liquibase_home: doesn\'t exist'
        module.fail_json(msg=msg, changed=False)
    
    if os.path.isfile(liquibase_home + '/liquibase.jar'):
        liquibase_jar = "%s/%s" % (liquibase_home, 'liquibase.jar')
    else:
        msg = 'liquibase.jar: not found in liquibase_home'
        module.fail_json(msg=msg, changed=False)

    if os.path.exists(("%s/lib") % (liquibase_home)):
        liquibase_lib = ("%s/lib") % (liquibase_home)
        paths.append(liquibase_lib)
    
    if module.params['schemas_dir'] and os.path.exists(module.params['schemas_dir']):
        schemas_dir = module.params['schemas_dir']
        liquibase_properties = ("%s/%s") % (module.params['schemas_dir'], module.params['defaultsFile'])
        liquibase_logFile = ("%s/%s") % (module.params['schemas_dir'], module.params['logFile'])
        paths.append(schemas_dir)
    else:
        msg = ("%s: not found" % module.params['schema_dir'])
        module.fail_json(msg=msg, changed=False)

    class_paths = []
    for path in paths:
        for root, dirs, files in os.walk(path):
            for name in files:
                if name.endswith('.jar'):
                    class_paths.append(os.path.join(root, name))
    
    classpath =  ".:%s:%s" % (liquibase_jar, ":".join(class_paths) )

    if os.path.isfile(module.params['changeLogFile']):
        changeLogFile = module.params['changeLogFile']
    elif os.path.isfile("%s/db.changelog-master.xml" % schemas_dir):
        changeLogFile = ("%s/db.changelog-master.xml" % schemas_dir)
    else:
        msg = ("%s: not found" % module.params['changeLogFile'])
        module.fail_json(changes=False, msg=msg)

    url = ("jdbc:oracle:thin:@//%s:%d/%s\n" % (module.params['hostname'], module.params['port'], module.params['service_name']))

    command = module.params['command']
    if module.get_bin_path('java', True):
        java_bin = module.get_bin_path('java', True)
    else:
        module.fail_json(changed=False, msg='java: not found')

    if module.params['contexts'] and module.params['contexts'] != '':
        contexts = ('--contexts=%s' % module.params['contexts'])
    else:
        contexts = ''

    if module.params['parameters']:
        parameters = (' %s' % module.params['parameters'])
    else:
        parameters = ''

    if module.params['java_parameters']:
        java_parameters = ('%s' % module.params['java_parameters'])
    else:
        java_parameters = ''

    liquibase_cmd = ("%s -cp %s liquibase.integration.commandline.Main %s %s %s %s") % (java_bin, classpath, contexts, parameters, command, java_parameters)


    if module.check_mode:
        msg=('Liquibase \'%s\' Successful' % command)
        module.exit_json(changed=False, cmd=liquibase_cmd, url=url, result=msg, check_mode=module.check_mode)

    os.chdir(schemas_dir)
    fh = open(liquibase_properties, "w")
    liquibase_properties_content = [
        ("driver: %s\n" % module.params['driver']),
        ("classpath: %s\n" % classpath),
        ("url: jdbc:oracle:thin:@//%s:%d/%s\n" % (module.params['hostname'], module.params['port'], module.params['service_name'])),
        ("username: %s\n" %  module.params['username']),
        ("password: %s\n" % module.params['password']),
        ("changeLogFile: %s\n" % changeLogFile),
        ("referenceUrl: jdbc:oracle:thin:@//%s:%d/%s\n" % (module.params['hostname'], module.params['port'], module.params['service_name'])),
        ("referenceUsername: %s\n" % module.params['username']),
        ("referencePassword: %s\n" % module.params['password']),
        ("logLevel: %s\n" % module.params['logLevel'])]
    if not module.params['print_log']:
        liquibase_properties_content.append("logFile: %s" % liquibase_logFile)
    fh.writelines(liquibase_properties_content)
    fh.close()

    rc, liquibase_stdout, liquibase_err = module.run_command(liquibase_cmd, cwd=schemas_dir)
    if rc != 0:
        msg=('Liquibase \'%s\' Failed' % command)
        if module.params['print_log']:
            module.fail_json(changed=True, cmd=liquibase_cmd, stdout_lines=liquibase_err, url=url, msg=msg, rc=rc)
        else:
            module.fail_json(changed=True, cmd=liquibase_cmd, url=url, msg=msg, rc=rc)
    elif rc == 0:
        msg=('Liquibase \'%s\' Successful' % command)
        if module.params['print_log']:
            module.exit_json(changed=True, cmd=liquibase_cmd, stdout_lines=liquibase_err, url=url, msg=msg, rc=rc)
        else:
            module.exit_json(changed=True, msg=msg, rc=rc)

def main():
    run_module()

if __name__ == '__main__':
    main()