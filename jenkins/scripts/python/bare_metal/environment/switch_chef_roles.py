#!/usr/bin/python
import os
import json
import argparse
from razor_api import razor_api
from ssh_session import ssh_session
import time
from chef import *


parser = argparse.ArgumentParser()
# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Razor policy to set chef roles for.")

parser.add_argument('--data_bag_location', action="store", dest="data_bag_loc",
                    default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node", 
                    required=False, help="Location of chef data bags")

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

#############################################################
#Collect active models that match policy from given input
#############################################################

razor = razor_api(results.razor_ip)
policy = results.policy
roles = ['role[qa-single-controller]', 'role[qa-single-api]', 'role[qa-single-compute]']

print "#################################"
print " Switching roles and running chef-client for  '%s'  active models" % policy
print "Display only: %s " % results.display_only

active_models = razor.simple_active_models(policy)

if active_models == {}:
    print "'%s' active models: 0 " % (policy)
    print "#################################"
else:
    if 'response' in active_models.keys():
        active_models = active_models['response']
    
    print "'%s' active models: %s " % (policy, len(active_models))
    print "#################################"


    # Gather all of the active models for the policy and get information about them
    i = 0
    for active in active_models:
        data = active_models[active]
        chef_name = get_chef_name(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)
            run_list = node.run_list
            role = node.role
            environment = node.chef_environment
            
            if results.display_only == 'true':
                if (i > len(roles) - 1):
                    i = len(roles) - 1
                print "!!## -- "
                print "!!## -- %s has role: %s ,run list: %s, and environment: %s -- ##!!" % (node, role, run_list, environment)
                print "!!## -- %s run list will be switched to %s with environment %s -- ##!!" % (node, roles[i], policy)
                i += 1
            else:
                # set the environment and run lists
                # this is for our QA environment of 4 servers (2 api, 2 compute), might make script take roles -> numbers at a later date
                print "!!## --   "
                print "!!## -- %s has run list: %s, and environment: %s -- ##!!" % (node, run_list, environment)
                environment = policy
                if i == 0:
                    print "!!## -- First host %s, set to role %s -- ##!!" % (node, roles[i])
                    run_list = [roles[i]]
                    i += 1
                elif i == 1:
                    print "!!## -- Second host %s, set to role %s -- ##!!" % (node, roles[i])
                    run_list = [roles[i]]
                    i += 1
                else:
                    print "!!## -- Non API host %s, set to role %s -- ##!!" % (node, roles[i])
                    run_list = [roles[i]]

                node.run_list = run_list
                node.chef_environment = environment

                try:
                    node.save()
                    print "!!## -- NODE: %s SAVED -- ##!!" % node
                    print "!!## -- NEW ROLE: %S" % node.role
                    print "!!## -- NEW RUN LIST: %s" % node.run_list
                    print "!!## -- NEW ENVIRONMENT: %s" % node.chef_environment
                except Exception, e:
                    print "!!## -- Failed to save node -- Exception: %s -- ##!!" % e
