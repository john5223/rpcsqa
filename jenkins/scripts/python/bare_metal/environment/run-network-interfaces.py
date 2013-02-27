#!/usr/bin/python
import os
import sys
import json
import time
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Razor policy to set chef roles for.")

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

# Save the parsed arguments
results = parser.parse_args()

# converting string display only into boolean
if results.display_only == 'true':
    display_only = True
else:
    display_only = False

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

print "!!## -- Switching roles for  '%s'  active models -- ##!!" % policy
print "!!## -- Display only: %s -- ##!!" % results.display_only

# Gather the active models with the policy from the cmd line
active_models = razor.simple_active_models(policy)

if active_models:
    # Gather all of the active models for the policy and get information about them
    i = 0
    failed_run = False
    for active in active_models:
        data = active_models[active]
        chef_name = get_chef_name(data)
        password = get_root_pass(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)
            environment = node.chef_environment
            ip = node['ipaddress']

            # set the nodes environment
            if environment != policy:
                environment = policy
                try:
                    node.chef_environment = environment
                    node.save()
                    print "!!## -- Node: %s saved with environment %s -- ##!!" % (node, node.chef_environment)
                except Exception, e:
                    print "!!## -- Failed to save node environment -- Exception: %s -- ##!!" % e
                    sys.exit(1)
            else:
                print "!!## -- Node %s already had the correct environment, no change" % node

            # add network_interfaces to the nodes run run_list
            try:
                node.run_list.append('recipe[network-interfaces]')
                node.save()
                print "!!## -- Node: %s saved with new run list %s -- ##!!" % (node, node.run_list)
            except Exception, e:
                print "!!## -- Failed to save node %s with new run list -- Exception: %s -- ##!!" % (node, e)
                sys.exit(1)

            # sleep for 5 seconds to give chef time
            time.sleep(5)

            # Once the recipe is added, run chef-client
            try:
                check_call_return = check_call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'chef-client;chef-client'" % (password, ip), shell=True)
                print "!!## -- Successful chef-client run on server with ip %s -- ##!!" % ip
            except CalledProcessError, cpe:
                print "!!## -- Failed to run chef-client on server with ip: %s -- ##!!" % ip
                print "!!## -- Return Code: %s -- ##!!" % cpe.returncode
                #print "!!## -- Command: %s -- ##!!" % cpe.cmd
                print "!!## -- Output: %s -- ##!!" % cpe.output
                failed_run = True

            # Sleep for 5 second to give chef time
            time.sleep(5)

    # If a run failed, fail the script
    if failed_run:
        print "!!## -- One or more of the chef-client runs failed, see logs -- ##!!"
        sys.exit(1)
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)