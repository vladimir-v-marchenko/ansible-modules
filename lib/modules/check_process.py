#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stable'],
                    'supported_by': ' "Special DHL-MNT DevOps <SpecialDHL-MNTDevOps@epam.com>"'}


DOCUMENTATION = '''
---
module: check_process
author: Serge van Ginderachter
version_added: "1.2"
short_description: Check processes and maybe kill them
description:
    - Checks (number of) running processes for a given command argument and
      can kill those matching processes, with increasing kill signal priority
options:
    name:
        required: true
        description:
        - name of the process, a substring to look for as would be
          found in the output of the I(ps) command; matches against full
          process argument string (as per ps auxww)
    count:
        required: false
        description:
        - exact number of processes that should be found in the process list;
          if 0, processess will be killed, which is the only case where action
          is taken to modify the target system;
          use of count excludes use of mincount or maxcount
    mincount:
        required: false
        default: 0
        description:
        - minimum number of processes that should be found in the process list;
          if set, module will fail if less processes are found
    maxcount:
        required: false
        description:
        - maximum number of processes that should be found in the process list;
          if set, module will fail if more processes are found
    wait:
        required: false
        default: 60,5
        description:
        - times in seconds to wait before checking the process list again,
          for process(es) to disappear from the process list, after receiving
          a kill signal; there must be at least as many wait times as there are
          killsignals; only used when count=0
    killsignals:
        required: false
        default: SIGTERM,SIGKILL
        description:
        - comma-separated ordered list of signals(7), used to sequentially
          terminate the process when count is set to 0
          if set to C(NOKILL), no kill will be executed, but will still wait for
          proces to come down, handy to use after e.g. an init stop script


examples:
    - description: checks that exactly 1 process is running of this custom tomcat service
      code: "check_process: name=/opt/tomcat/apache-tomcat7/lib/ count=1"
    - description: force kill all running java processes
      code: "check_process: name=java count=0 killsignals=SIGKILL"
    - description: check for at least 10 apache processes
      code: "check_process: name=apache2 mincount=10"
'''

import platform
import time

from ansible.module_utils.basic import AnsibleModule

KILLSIGNALS = 'SIGTERM,SIGKILL'
WAITTIMES = '30,5'

def get_pids(module):
    ''' returns a list of pid's matching the name pattern'''

    pattern = module.params['name']

    # Find ps binary
    psbin = module.get_bin_path('ps', True)

    # Set ps flags
    if platform.system() == 'SunOS':
        psflags = '-ef'
    else:
        psflags = 'auxww'

    # run ps command
    cmd = '%s %s' % (psbin, psflags)
    (rc, out, err) = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg='Fatal error running command %s' % cmd, stdout=out, stderr=err)

    # parse ps output into list of pid's
    pids = []
    lines = out.split("\n")
    for line in lines:
        # exclude ps itself, hacking/test-module script
        if pattern in line and not 'test-module' in line:
            # add second PID column to list
            pids.extend([line.split()[1]])
    return pids


def kill_process(module, pids, signal):
    # Find kill binary
    killbin = module.get_bin_path('kill', True)

    # put pid list in a space separate string
    pids_str = ' '.join(str(x) for x in pids )

    # kill --signal <signal> <pid1 pid2  ...>
    cmd = '%s -%s %s' % (killbin, signal, pids_str)
    if signal == 'NOKILL':
        # don't execute any kill command
        cmd = ': ' + cmd
    (rc, out, err) = module.run_command(cmd)


def kill_process_wait(module, pids, signal, wait):
    kill_process(module, pids, signal)

    t0 = time.time()
    while 1:
        pids = get_pids(module)
        running = len(pids)
        if running == 0 or (time.time() - t0) >= int(wait):
            break
        # wait for processes to shut down or until timeout 'wait'
        time.sleep(1)

    return pids


def check_with_count(module, result, fail):

    count = module.params['count']
    # convert comma separated kilsignals into list
    killsignals = module.params['killsignals'].split(',')
    waittimes = module.params['wait'].split(',')

    if len(killsignals) > len(waittimes):
        module.fail_json(msg='you need at least as many wait times (got %s) as killsignals (got %s)' % (len(killsignals), len(waits)))

    pids = get_pids(module)
    running = len(pids)

    # kill! kill! kill!
    if count == 0:

        if running == 0 or module.check_mode:
            # nothing to do, zero killed, or
            # there are active processes, but we are in check mode,
            # so we assume all got killed
            still_running = 0
            signal = None

        elif not module.check_mode:
            # there are active processes so now really kill them all
            # loop through the kill signals in order, and try killing the process(es)

            t0 = time.time()
            for n in range(len(killsignals)):
                signal = killsignals[n]
                wait = waittimes[n]
                pids = kill_process_wait(module, pids, signal, wait)
                # still running after kill?
                still_running = len(pids)
                if still_running == 0:
                    break
            result['time_elapsed'] = '%s s' % (time.time() - t0)

        killed = running - still_running
        result['still_running'] = still_running
        result['killed'] = killed
        result['signal'] = signal
        result['msg'] = 'killed %s processes' % killed

        # changed is only true when we killed
        if killed != 0:
            result['changed'] = True

        # if we killed as much as was running, exit ok
        if killed != running:
            fail = True

    # check if we have the right number of running processes
    elif count > 0:
        if count == running:
            result['msg'] = 'Number of running processes (%s) is equal to %s' % (running, count)
        else:
            result['msg'] = 'Number of running processes (%s) is not equal to %s' % (running, count)
            fail = True

    else:
        result['msg'] = 'count cannot be negative'
        fail = True

    return (result, fail)


def check_with_minmaxcount(module, result, fail):

    mincount = module.params['mincount']
    maxcount = module.params['maxcount']

    pids = get_pids(module)
    running = len(pids)

    if mincount is not None and maxcount is not None:
        if mincount >= maxcount:
            result['msg'] = 'Minimum (%s) should be smaller than maximum (%s)' % (mincount, maxcount)
            fail = True

        elif mincount <= running <= maxcount:
            result['msg'] = 'Number of running processes (%s) is in the range %s -> %s.' % (running, mincount, maxcount)
        else:
            result['msg'] = 'Number of running processes (%s) is not in the range %s -> %s.' % (running, mincount, maxcount)
            fail = True
    elif mincount is not None:
        if mincount <= running:
            result['msg'] = 'Number of running processes (%s) is larger than %s' % (running, mincount)
        else:
            result['msg'] = 'Number of running processes (%s) is smaller than %s' % (running, mincount)
            fail = True
    elif maxcount is not None:
        result['maxcount'] = maxcount
        if running <= maxcount:
            result['msg'] = 'Number of running processes (%s) is smaller than %s' % (running, maxcount)
        else:
            result['msg'] = 'Number of running processes (%s) is larger than %s' % (running, maxcount)
            fail = True

    return (result, fail)


def main():
    # load ansible module object
    module = AnsibleModule(
        argument_spec = dict(
            name = dict(required=True),
            count = dict(required=False, default=None, type='int'),
            mincount = dict(required=False, type='int'),
            maxcount = dict(required=False, type='int'),
            wait = dict(required=False, default=WAITTIMES),
            killsignals = dict(required=False, default=KILLSIGNALS)
        ),
        supports_check_mode=True,
        mutually_exclusive=[['count', 'mincount'], ['count', 'maxcount']],
        required_one_of=[['count', 'mincount' , 'maxcount']]
    )
    name = module.params['name']
    count = module.params['count']
    mincount = module.params['mincount']
    maxcount = module.params['maxcount']

    # return json dict
    result = {}
    result['name'] = name

    # retrieve pids matching the name pattern
    pids = get_pids(module)
    result['pids'] = pids

    # set number of running processes we found
    running = len(pids)
    result['running'] = running

    # set default changed false; is only true when we killed
    result['changed'] = False
    # default no fail
    fail = False

    # if count is set
    if count is not None:
        result['count'] = count
        (result, fail) = check_with_count(module, result, fail)

    # check with mincount and/or maxcount
    elif mincount is not None or maxcount is not None:
        result['mincount'] = mincount
        result['maxcount'] = maxcount
        (result, fail) = check_with_minmaxcount(module, result, fail)

    if fail:
        module.fail_json(**result)
    else:
        module.exit_json(**result)

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>

if __name__ == '__main__':
    main()
