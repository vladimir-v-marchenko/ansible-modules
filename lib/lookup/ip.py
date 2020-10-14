from ansible import errors
from ansible.plugins.lookup import LookupBase
import socket
from six import string_types


class LookupModule(LookupBase):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, variables=None, **kwargs):
        '''
        Get hostname and return its IP address.
        Doesn't require any additional python libraries.
        Jira task: DHLEWFCON-66016
        '''

        hostname = terms[0]

        if not isinstance(hostname, string_types):
            raise errors.AnsibleError("lookup_plugin ip | expect hostname (string), got " + repr(hostname))

        return [socket.gethostbyname(hostname)]
