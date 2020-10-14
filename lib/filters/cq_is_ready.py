from ansible import errors


def cq_is_ready(values_dict, symbolic_name='com.day.cq.workflow.cq-workflow-impl', state='Active'):
    '''
    Get array of dictionaries and compare dictionary's
    values with given in parameters.

    Jira task: DHLEWFCON-50618
    '''

    # Check if parameter types are correct
    if not isinstance(values_dict, dict):
        raise errors.AnsibleFilterError("cq_is_ready | expect CQ packages dictionary, got " + repr(values_dict))
    if not isinstance(symbolic_name, str):
        raise errors.AnsibleFilterError("cq_is_ready | expect name of CQ package (string), got " + repr(symbolic_name))
    if not isinstance(state, str):
        raise errors.AnsibleFilterError("cq_is_ready | expect state of CQ package (string), got " + repr(state))

    # Check if CQ reply is not empty
    if ('json' not in values_dict) or ('data' not in values_dict['json']):
        return False

    for value in values_dict['json']['data']:
        if (value['symbolicName'] == symbolic_name) and (value['state'] == state):
            return True
    return False


class FilterModule(object):
    '''
    Ansible custom filter plugin
    '''
    def filters(self):
        return {
            'cq_is_ready': cq_is_ready,
        }
