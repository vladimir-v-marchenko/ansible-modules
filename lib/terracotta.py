# Install the Python Requests library:
# `pip install requests`

from __future__ import absolute_import, division, print_function


import cgi
import datetime
import json
import os
import shutil
import sys
import tempfile
import traceback

from collections import Mapping, Sequence
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import PY2, iteritems, string_types
from ansible.module_utils.six.moves.urllib.parse import urlencode, urlsplit
from ansible.module_utils._text import to_native, to_text


from ansible.module_utils.urls import Request
r = Request()
r.open('GET', 'http://httpbin.org/cookies/set?k1=v1').read()


#         >>> r = Request(url_username='user', url_password='passwd')
#         >>> r.open('GET', 'http://httpbin.org/basic-auth/user/passwd').read()
#         '{\n  "authenticated": true, \n  "user": "user"\n}\n'
#         >>> r = Request(headers=dict(foo='bar'))
#  >>> r.open('GET', 'http://httpbin.org/get', headers=dict(baz='qux')).read()



# import requests


# def __login():
#     # Request
#     # POST https://aqatwin2.tc-1.dhl-ewf.kyiv.epam.com:9443/tmc/login.jsp

#     try:
#         response = requests.post(
#             url="https://aqatwin2.tc-1.dhl-ewf.kyiv.epam.com:9443/tmc/login.jsp",
#             headers={
#                 "Accept": "text/html,application/xml",
#                 "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
#                 # "Cookie": "JSESSIONID=4b3eaa68-6c84-4eae-aa87-ac8f189978e7; JSESSIONID=38be2655-630a-4e25-93ea-f9761361991b; JSESSIONID=node01d3lh8so0n9su1xmddwqfs7qly174.node0",
#             },
#             data={
#                 "username": "tc_user",
#                 "password": "nIj12lQsrnKYcXeQ21dHw2I7dprTmfF7!",
#             },
#         )
#         print('Response HTTP Status Code: {status_code}'.format(
#             status_code=response.status_code))
#         print('Response HTTP Response Body: {content}'.format(
#             content=response.content))
#     except requests.exceptions.RequestException:
#         print('HTTP Request failed')


# # Install the Python Requests library:
# # `pip install requests`



# def send_request():
#     # Request (2)
#     # POST https://aqatwin2.tc-1.dhl-ewf.kyiv.epam.com:9443/tmc/api/agents/cacheManagers/caches

#     try:
#         response = requests.post(
#             url="https://aqatwin2.tc-1.dhl-ewf.kyiv.epam.com:9443/tmc/api/agents/cacheManagers/caches",
#             headers={
#                 "Cookie": "",
#             },
#         )
#         print('Response HTTP Status Code: {status_code}'.format(
#             status_code=response.status_code))
#         print('Response HTTP Response Body: {content}'.format(
#             content=response.content))
#     except requests.exceptions.RequestException:
#         print('HTTP Request failed')



# def main