import argparse
from opencenter_helper import openstack_endpoints
import requests
import json
import sys
from pprint import pprint
from subprocess import check_call, CalledProcessError

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()
parser.add_argument('--name', action="store", dest="name",
                    required=False, default="test",
                    help="Name for the opencenter chef environment")
parser.add_argument('--os', action="store", dest="os", required=False,
                    default='ubuntu',
                    help="Operating System to use for opencenter")
parser.add_argument('--tempest_dir', action="store", dest="tempest_dir",
                    required=False,
                    default="/var/lib/jenkins/tempest/folsom/tempest")
parser.add_argument('--tempest_version', action="store",
                    dest="tempest_version", required=False,
                    default="folsom")
parser.add_argument('--keystone_admin_pass', action="store",
                    dest="keystone_admin_pass", required=False,
                    default="secrete")
results = parser.parse_args()

# Gather information of cluster

ip = next(openstack_endpoints(name='cameron', os='ubuntu'))
url = "http://%s:5000/v2.0" % ip
token_url = "%s/tokens" % url
print "##### URL: %s #####" % url
auth = {
    'auth': {
        'tenantName': 'admin',
        'passwordCredentials': {
            'username': 'admin',
            'password': '%s' % results.keystone_admin_pass
        }
    }
}

# Gather cluster information from the cluster
image_id = None
image_alt = None
try:
    r = requests.post(token_url, data=json.dumps(auth),
                      headers={'Content-type': 'application/json'})
    ans = json.loads(r.text)
    if 'error' in ans.keys():
        pprint(ans['error'])
        sys.exit(1)
    token = ans['access']['token']['id']
    images_url = "http://%s:9292/v2/images" % ip
    images = json.loads(requests.get(images_url,
                        headers={'X-Auth-Token': token}).text)
    image_ids = (image['id'] for image in images['images'])
    image_id = next(image_ids)
    image_alt = next(image_ids, image_id)
    print "##### Image 1: %s #####" % image_id
    print "##### Image 2: %s #####" % image_alt
except Exception, e:
    print "Failed to add keystone info. Exception: %s" % e
    sys.exit(1)

# Write the config
try:
    sample_path = "%s/etc/base_%s.conf" % (results.tempest_dir,
                                           results.tempest_version)
    with open(sample_path) as f:
        sample_config = f.read()
    tempest_config = str(sample_config)
    tempest_config = tempest_config.replace('http://127.0.0.1:5000/v2.0/',
                                            url)
    tempest_config = tempest_config.replace('{$KEYSTONE_IP}', ip)
    tempest_config = tempest_config.replace('localhost', ip)
    tempest_config = tempest_config.replace('127.0.0.1', ip)
    tempest_config = tempest_config.replace('{$IMAGE_ID}', image_id)
    tempest_config = tempest_config.replace('{$IMAGE_ID_ALT}',
                                            image_alt)
    tempest_config = tempest_config.replace('ostackdemo',
                                            results.keystone_admin_pass)
    tempest_config = tempest_config.replace('demo', "admin")
   
    tempest_config_path = "%s/etc/%s-%s.conf" % \
                          (results.tempest_dir, results.name,
                           results.os)
    with open(tempest_config_path, 'w') as w:
        print "####### Tempest Config #######"
        print tempest_config_path
        print tempest_config
        w.write(tempest_config)
   
except Exception as e:
    print "Failed writing tempest config, exception: %s" % e
    sys.exit(1)

# Run tests
try:
    print "!! ## -- Running tempest -- ## !!"
    
    check_call_return = check_call(
        "export TEMPEST_CONFIG=%s; python -u /usr/local/bin/nosetests %s/tempest/tests/compute" % (tempest_config_path, results.tempest_dir), shell=True)
    print "!!## -- Tempest tests ran successfully  -- ##!!"
except CalledProcessError, cpe:
    print "!!## -- Tempest tests failed -- ##!!"
    print "!!## -- Return Code: %s -- ##!!" % cpe.returncode
    print "!!## -- Output: %s -- ##!!" % cpe.output
    sys.exit(1)
