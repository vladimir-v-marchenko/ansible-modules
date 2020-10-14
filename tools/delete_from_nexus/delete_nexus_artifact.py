#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Delete specific artifact from Nexus."""
from __future__ import print_function
from urlparse import urlparse

import argparse
import base64
import httplib
import string
import sys

from ConfigParser import SafeConfigParser


def _parse_url(url):
    """Return host and port from nexus_url"""
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    if parsed_url.port is None:
        if parsed_url.scheme == 'http':
            port = '80'
        elif parsed_url.scheme == 'https':
            port = '443'
    else:
        port = parsed_url.port
    return (host, port)


def _prepare_url(args):
    url = '{}/service/local/repositories/{}/content/{}/{}/{}'.format(
        args.nexus_url,
        args.repository,
        args.group_id.replace('.', '/'),
        args.artifact_id,
        args.version
    )

    return url


def _encode_credentials(username, password):
    auth = string.strip(base64.encodestring('{}:{}'.format(
        username,
        password
    )))

    return auth


def _send_request(url, auth):
    host, port = _parse_url(url)
    try:
        service = httplib.HTTP(host, port)
        service.putrequest('DELETE', url)
        service.putheader('Host', host)
        service.putheader('User-Agent', 'Python http auth')
        service.putheader('Content-type', "text/html; charset='UTF-8'")
        service.putheader('Authorization', 'Basic {}'.format(auth))
        service.endheaders()
        service.send('')
    except Exception as e:
        print(e)
        exit(0)

    statuscode, statusmessage, header = service.getreply()

    if statuscode == 404:
        result = 'Artifact already removed'
    elif statuscode == 204:
        result = 'Artifact removed successfully'
    elif statuscode >= 301 and statuscode < 400:
        result = _send_request(url=header['location'], auth=auth)
    else:
        result = 'Response: {} {}'.format(statuscode, statusmessage)

    return result


def remove_artifact(args):
    """Remove artifact from Nexus."""
    url = _prepare_url(args)
    print('Sending HTTP DELETE request to {}'.format(url))

    auth = _encode_credentials(args.nexus_username, args.nexus_password)
    result = _send_request(url, auth)
    print(result)


def parse_args():
    """Parse arguments from configuration file and command line."""
    # The next block is done so the configuration file location can be passed
    # as a command-line parameter and it's content parsed and passed as default
    # values for the argparse
    configfile = None
    for idx, val in enumerate(sys.argv):
        if val == '-c' or val == '--config':
            configfile = sys.argv[idx + 1]
            break

    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument('-c', '--config',
                               dest='config_path',
                               type=str,
                               help='Path to configuration',
                               default='configuration.cfg')
    if configfile:
        parent_args = parent_parser.parse_args(['-c', configfile])
    else:
        parent_args = parent_parser.parse_args([])

    config_parser = SafeConfigParser()
    config_parser.read(parent_args.config_path)

    parser = argparse.ArgumentParser(parents=[parent_parser])

    parser.add_argument('--url',
                        dest='nexus_url',
                        type=str,
                        help='Nexus server url',
                        default=config_parser.get('nexus', 'url')
                        if 'nexus' in config_parser.sections() else '')

    parser.add_argument('--username',
                        dest='nexus_username',
                        type=str,
                        help='Nexus username',
                        default=config_parser.get('nexus', 'username')
                        if 'nexus' in config_parser.sections() else '')

    parser.add_argument('--password',
                        dest='nexus_password',
                        type=str,
                        help='Nexus password',
                        default=config_parser.get('nexus', 'password')
                        if 'nexus' in config_parser.sections() else '')

    parser.add_argument('--repository',
                        dest='repository',
                        type=str,
                        help='Repository',
                        default=config_parser.get('artifact', 'repository')
                        if 'artifact' in config_parser.sections() else '')

    parser.add_argument('--artifact',
                        dest='artifact_id',
                        type=str,
                        help='Artifact ID',
                        required=True)

    parser.add_argument('--group',
                        dest='group_id',
                        type=str,
                        help='Artifact group ID',
                        required=True)

    parser.add_argument('--version',
                        dest='version',
                        type=str,
                        help='Artifact version',
                        required=True)

    args = parser.parse_args()
    return args


def main():
    """Execute useful code."""
    args = parse_args()
    remove_artifact(args)


if __name__ == '__main__':
    main()
