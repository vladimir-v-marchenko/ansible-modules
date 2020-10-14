#!/usr/bin/env python

# Copyright 2017, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

import yaml


def load_file(file_path):
    if os.path.exists(file_path):
        with open(file_path) as f:
            x = yaml.load(f.read())

        if lookup in x:
            return x[lookup]


def path_search(path, lookup):
    print('Searching ["%s"]' % path)
    for _path, dirs, files in os.walk(path):
        for _file in files:
            if _file.endswith(('yaml', 'yml')):
                resultant = load_file(file_path=os.path.join(_path, _file))
                if resultant:
                    return resultant
        else:
            for _dir in dirs:
                path_search(path=os.path.join(_path, _dir), lookup=lookup)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(
            'Command syntax: %s ${FILE|DIRECTORY} ${LOOKUP}' % sys.argv[0]
        )
    else:
        yaml_file = sys.argv[1]
        lookup = sys.argv[2]
        if not os.path.isdir(yaml_file):
            lookup_item = load_file(file_path=yaml_file)
        else:
            lookup_item = path_search(path=yaml_file, lookup=lookup)
        if lookup_item:
            print(yaml.safe_dump([lookup_item], 
                                 default_flow_style=False, 
                                 width=1000))
        else:
            raise SystemExit('Lookup not found')
