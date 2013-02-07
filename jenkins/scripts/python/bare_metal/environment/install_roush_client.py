#!/usr/bin/python
import os
import sys
import subprocess
import json
import argparse
from razor_api import razor_api
import time
from chef import *


parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    default="qa-roush-client",
                    required=True, help="Razor policy to set chef roles for.")

parser.add_argument('--role', action="store", dest="role", 
                    required=True, help="Chef role to run chef-client on")

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

def get_chef_name(data):
    try:
        name = "%s%s.%s" % (data['hostname_prefix'], data['bind_number'], data['domain'])
        return name
    except Exception, e:
        return ''

def get_root_pass(data):
    if 'root_password' in data:
        return data['root_password']
    else:
        return ''

#############################################################
#Collect active models that match policy from given input
#############################################################

razor = razor_api(results.razor_ip)
policy = results.policy

print "#################################"
print " Attempting to install roush client for role %s " % results.role
print "Display only: %s " % results.display_only

active_models = razor.simple_active_models(policy)
to_run_list = []
if active_models == {}:
    print "'%s' active models: 0 " % (policy)
    print "#################################"
else:
    if 'response' in active_models.keys():
        active_models = active_models['response']
    print "'%s' active models: %s " % (policy, len(active_models))
    print "#################################"

    # Gather all of the active models for the policy and get information about them
    roush_server_ip = ''
    for active in active_models:
        data = active_models[active]
        chef_name = get_chef_name(data)
        root_password = get_root_pass(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)
            if 'role[qa-roush-server]' in node.run_list:
                roush_server_ip = node['ipaddress']
                print "Roush Server Node: %s with ip %s" % (node, roush_server_ip)

            if 'role[%s]' % results.role in node.run_list:
                ip = node['ipaddress']
            
                if results.display_only == 'true':
                    print "!!## -- ROLE %s FOUND,  %s with ip %s..." % (results.role, node, ip)
                else:
                    print "!!## -- ROLE %s FOUND, installing roush client on %s with ip %s..." % (results.role, node, ip)
                    to_run_list.append({'node': node, 'ip': ip, 'root_password': root_password})

    if results.display_only == 'false':
        for server in to_run_list:
            print "Setting ROUSH_SERVER environment variable to %s on server %s" % (roush_server_ip, server['node'])
            try:
                return_code = subprocess.call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'export ROUSH_SERVER=%s'" % (server['root_password'], server['ip'], roush_server_ip), shell=True)
                if return_code == 0:
                    print "Successfully exported %s to environment variable ROUSH_SERVER" % roush_server_ip
                else:
                    print "Failed to set ROUSH_SERVER environment variable for server %s @ ip: %s, exited with code %s" % (server['node'], server['ip'], return_code)
                    pass
            except Exception, e:
                print "Failed to set ROUSH_SERVER environment variable for server %s @ ip: %s, error: %s" % (server['node'], server['ip'], e)

            """
            print "Attempting to install roush client on %s with ip %s...." % (server['node'], server['ip'])
            try:
                return_code = subprocess.call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'curl -L https://bcd46edb6e5fd45555c0-409026321750f2e680f86e05ff37dd6d.ssl.cf1.rackcdn.com/install-agent.sh | bash'" % (server['root_password'], server['ip']), shell=True)
                if return_code == 0:
                    print "chef-client success..."
                else:
                    print "chef-client failed..."
                    sys.exit(1)

            except Exception, e:
                print "chef-client FAILURE: %s " % e
            """
