#!/usr/bin/env python3

import requests as req

files={
    'r': (None,'other'),
    'hasPom': (None,'false'),
    'e': (None,'jar'),
    'g': (None,'com.dhl.ewf.esb.commons'),
    'a': (None,'test'),
    'v': (None,'qa-40.20-7'),
    'p': (None,'jar'),
    'file': ('dhl-commons-qa-40.20-7.jar',open('/tmp/dhl-commons-qa-40.20-7.jar','rb'))
}

response=req.post('http://nexus-ua2.local/service/local/artifact/maven/content',files=files,auth=('admin','PassWord'));
print(response)

# response=requests.post('http://czcholsint969.prg-dc.dhl.com/nexus/service/local/artifact/maven/content',files=files,auth=('admin','PassWord'));
# print(response)

# curl -X POST "http://nexus-ua2.local/service/rest/v1/components?repository=other" -H  "accept: application/json" -H  "Content-Type: multipart/form-data" -F "maven2.groupId=com.dhl.ewf.esb.commons" -F "maven2.artifactId=dhl-commons" -F "maven2.version=qa-40.20-7" -F "maven2.generate-pom=true" -F "maven2.packaging=jar" -F "maven2.asset1=@dhl-commons-qa-40.20-7.jar;type=application/java-archive" -F "maven2.asset1.extension=jar"