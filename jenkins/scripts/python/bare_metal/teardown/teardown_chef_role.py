#!/usr/bin/python
import os
import sys
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

"""
This script will tear down razor server based on their chef roles and environments
"""

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")

parser.add_argument('--chef_environment', action="store", dest="chef_environment", required=True, 
                    help="This will be the environment to look in for Razor active models")

parser.add_argument('--chef_role', action="store", dest="chef_role", required=True, help='The chef role to tear down')

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.3:4000", required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, 
                    help="Display the node information only (will not reboot or teardown am)")

# Save the parsed arguments
results = parser.parse_args()

# converting string display only into boolean
if results.display_only == 'true':
    display_only = True
else:
    display_only = False

"""
Steps
1. Gather all the nodes in the given environment
2. Gather all the nodes whos role is not qa based
3. Find the role in the environment
4. Find the name of the node that has the role
5. Find the active model in razor with the node name found
6. Tear it down ( remove chef node, client, active model, then reboot)
"""
with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)
    nodes = Search('node').query("chef_environment:%s" % results.chef_environment)
    for n in nodes:
        print "Pre node name: %s" % n['name']
        node = Node(n['name'])
        # Debug Printing
        print "Name: %s" % node.attributes['name']
        print "IP: %s" % node.attributes['ipaddress']
        print "run_list: %s" % node.run_list

        # Get the am uuid from chef
        am_uuid = node.attributes['razor_metadata']['razor_active_model_uuid']
        print "Razor AM UUID: %s" % am_uuid
        
        # Get the AM password from Razor
        try:
            passwd = razor.get_active_model_pass(am_uuid)
            if passwd['status_code'] == 200:
                print "Razor AM Password: %s" % passwd['password']
            else:
                print "!!## -- Error getting password for active model, exited with error code: %s -- ##!!" % passwd['status_code']
                sys.exit(1)
        except Exception, e:
            print "Error: %s" % e


