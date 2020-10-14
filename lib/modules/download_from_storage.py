#!/usr/bin/env python
"""Library for downloading artifacts from different storages."""

DOCUMENTATION = """
---
module: download_from_storage
short_description: Download and install an artifact from storage.
    See https://github.com/frostyslav/ansible-storage
author: Michiel Meeuwissen, Marc Bosserhoff, Rostyslav Fridman
options:
    nexus:
        required: true
        description:
    repository:
        required: true
        description:
            - Used repository
    destdir:
        required: false
        description:
            - The destination dir of the downloaded artifacts
            - Defaults to '/tmp/downloaded_artifacts'
    artifact_id:
        required: true
        description:
            - The artifact to download. The format is separated by ':' and
              will be connected like so: group_id:artifact_id:version
    extension:
        required: false
        description:
            - The artifact extension (Defaults to 'war')
    force:
        required: false
        description:
            - Forces the download of the artifacts if they are present
              in the target destination
    http_user:
        required: false
        description:
            - If the storage need a basic authentication, the user name
              can be provided here
    http_pass:
        required: false
        description:
            - If the storage need a basic authentication, the password
              can be provided here
"""

EXAMPLES = """
- name: Get artifact from Nexus
  download_from_storage:
    nexus=http://nexus.example.com
    artifactId=artifactId:group_id:version
    extension=jar
"""

from ansible.module_utils.basic import *
import base64
from datetime import datetime
import urllib2
from wsgiref.handlers import format_date_time
import xml.etree.ElementTree as ET


module = AnsibleModule(
    argument_spec=dict(
        nexus=dict(required=False),
        repository=dict(required=True),
        destdir=dict(required=False, default="/tmp/downloaded_artifacts"),
        filename=dict(required=False, default=None),
        artifactId=dict(required=True),
        extension=dict(required=False, default="war"),
        force=dict(required=False, default=False),
        http_user=dict(required=False, aliases=['username']),
        http_pass=dict(required=False, aliases=['password'])
    ),
    supports_check_mode=False
)


def _get_artifact_params(artifact_id):
    splitted_values = artifact_id.split(':')
    if len(splitted_values) < 3:
        msg = 'Can\'t parse the artifactId {0}, '.format(artifact_id) + \
            'it should be in the format artifactId:groupId:version'
        _fail_module_execution(msg)
    (group_id, artifact_id, version) = splitted_values[0:3]
    classifier = splitted_values[3] if len(splitted_values) >= 4 else ""
    postfix = '-' + classifier if classifier else ""

    return group_id, artifact_id, version, classifier, postfix


def _get_artifact_url(params):
    if params['nexus']:
        url = _prepare_nexus_url(params)
    return url, params['version']


def _set_auth_header(params):
    headers = {}
    if params['http_user'] and params['http_pass']:
        encoded_string = _encode_credentials(params['http_user'], params['http_pass'])
        headers['Authorization'] = "Basic {0}".format(encoded_string)

    return headers


def _set_if_modified_header(params):
    headers = {}

    if os.path.isfile(params['dest']) and not params['force']:
        headers['IF-Modified-Since'] = \
            format_date_time(time.mktime(datetime.fromtimestamp(
                os.path.getmtime(params['dest'])).timetuple()))

    return headers


def _get_parameters_from_ansible():
    return module.params


def _get_new_filename(params):
    filename = params['artifact_id'] + '-' + params['version'] \
        + params['postfix'] + '.' + params['extension']
    return filename


def _encode_credentials(http_user, http_pass):
    credentials = base64.encodestring('{0}:{1}'.format(http_user, http_pass)).strip()
    return credentials


def _fail_module_execution(msg):
    module.fail_json(
        changed=False,
        msg=msg
    )


def _parse_xml(xml, version_to_resolve):
    root = ET.fromstring(xml)
    if any(x in version_to_resolve.lower() for x in ['latest', 'release']):
        for version in root.findall('versioning'):
            return version.find(version_to_resolve.lower()).text
    elif 'SNAPSHOT' in version_to_resolve:
        return root.find(
            'versioning/snapshotVersions/snapshotVersion/value').text
    else:
        msg = 'Can\'t resolve artifact version {0}'.format(version_to_resolve)
        _fail_module_execution(msg)



def _prepare_nexus_url(params):
    url_classifier = '&c=' + params['classifier'] if params['classifier'] else ''

    url = params['nexus'] + '/service/local/artifact/maven/redirect?r=' + \
        params['repository'] + '&g=' + params['group_id'] + "&a=" + params['artifact_id'] + '&v=' + \
        params['version'] + '&e=' + params['extension'] + url_classifier

    return url


def _resolve_version(params):
    headers = _set_auth_header(params)
    request = urllib2.Request(params['url'] + '/maven-metadata.xml', None, headers)

    try:
        response = urllib2.urlopen(request)
    except Exception as e:
        if hasattr(e, 'reason'):
            msg = 'Can\'t resolve version {0} due to error: {1}'.format(params['version'], e.reason)
        else:
            msg = 'Can\'t resolve version {0} due to error: {1}'.format(params['version'], e)
        _fail_module_execution(msg)

    return _parse_xml(response.read(), params['version'])


def load_artifact(params):
    """Load artifact from storage."""
    result = {}
    headers = _set_auth_header(params)
    headers.update(_set_if_modified_header(params))

    if not os.path.exists(params['destdir']):
        os.mkdir(params['destdir'])

    request = urllib2.Request(params['url'], None, headers)

    try:
        response = urllib2.urlopen(request)

    except Exception as e:
        msg = ''
        if hasattr(e, 'code'):
            if e.code == 304:
                result['changed'] = False
                result['msg'] = 'File {0} already exists'.format(params['dest'])
                return result
        if hasattr(e, 'reason'):
            msg = 'Can\'t download file {0} due to error {1}'.format(params['url'], e.reason)
        else:
            msg = 'Can\'t download file {0} due to error {1}'.format(params['url'], e)
        _fail_module_execution(msg)

    if response.code == 200:
        with open(params['dest'], 'wb') as f:
            f.write(response.read())

    result['msg'] = 'OK'
    result['changed'] = True

    return result


def parse_parameters():
    """Parse parameters from ansible module."""
    ansible_params = _get_parameters_from_ansible()
    params = ansible_params
    params['group_id'], params['artifact_id'], params['version'], \
        params['classifier'], params['postfix'] = _get_artifact_params(ansible_params['artifactId'])
    params['url'], params['version'] = _get_artifact_url(params)
    if ansible_params['filename'] is None:
        params['filename'] = _get_new_filename(params)
    params['dest'] = params['destdir'] + '/' + params['filename']
    return params


def main():
    """Main execution flow."""
    params = parse_parameters()

    # Try to load artifact from storage
    result = load_artifact(params)

    module.exit_json(
        dest=params['dest'],
        filename=params['filename'],
        artifactId=params['artifactId'],
        url=params['url'],
        msg=result['msg'],
        changed=result['changed']
    )

main()
