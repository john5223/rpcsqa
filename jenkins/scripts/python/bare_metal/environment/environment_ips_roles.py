#!/usr/bin/python
import argparse
import json
from chef import *

parser = argparse.ArgumentParser()
parser.add_argument('--environment', action="store", dest="environment", 
                    required=True, help="Environment to get roles -> ips for")

parser.add_argument('--chef_url', action="store", dest="chef_url", 
                    default="http://198.101.133.4:4000", 
                    required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", 
                    default="jenkins", 
                    required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", 
                    default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem", 
                    required=False, help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", 
                    default="true", 
                    required=False, help="Display the node information only (will not reboot or teardown am)")

# Parse the parameters
results = parser.parse_args()

with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    servers = Search('node', 'chef_environment:%s' % results.environment)
    for server in servers:
        print "##!! -- -- ##!!"
        print "Server Name: %s\n" % server['name']
        print "Server IP Address %s\n" % json.dumps(server['automatic']['ipaddress'])
        print "Server Run List: %s\n" % json.dumps(server['run_list'])
        print "Server Roles: %s\n" % json.dumps(server['automatic']['roles'], indent=4)
