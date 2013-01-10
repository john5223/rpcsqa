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
                    required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--data_bag_location', action="store", dest="data_bag_loc",
                    default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node", 
                    required=False, help="Policy to teardown from razor and reboot nodes")

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

def get_root_pass(data):
    if 'root_password' in data:
        return data['root_password']
    else:
        return ''

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
roles = ["['role[qa-single-controller]']", "['role[qa-single-api]']", "['role[qa-single-compute]']"]

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
    private_ips = []
    for active in active_models:
        data = active_models[active]
        
        root_pass = get_root_pass(data)
        chef_name = get_chef_name(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)
            run_list = node.run_list
            environment = node.chef_environment
            
            if results.display_only == 'true':
                print "!!## -- %s has run list: %s, and environment: %s -- ##!!" % (node, run_list, environment)
                print "!!## -- %s run list will be switched to %s with environment %s -- ##!!" % (node, roles[i], policy)
                i += 1
            else:
                # set the environment and run lists
                # this is for our QA environment of 4 servers (2 api, 2 compute), might make script take roles -> numbers at a later date
                print "!!## -- %s has run list: %s, and environment: %s -- ##!!" % (node, run_list, environment)
                environment = policy
                if i == 0:
                    print "!!## -- First host, set to role %s -- ##!!" % roles[i]
                    run_list = roles[i]
                    private_ips.append({'private_ip': node['ipaddress'], 'root_pass': root_pass, 'role': roles[i]})
                    i += 1
                elif i == 1:
                    print "!!## -- Second host, set to role %s -- ##!!" % roles[i]
                    run_list = roles[i]
                    private_ips.append({'private_ip': node['ipaddress'], 'root_pass': root_pass, 'role': roles[i]})
                    i += 1
                else:
                    print "!!## -- Non API host, set to role %s -- ##!!" % roles[i]
                    run_list = roles[i]
                    private_ips.append({'private_ip': node['ipaddress'], 'root_pass': root_pass, 'role': roles[i]})

                node.run_list = run_list
                node.chef_environment = environment

                try:
                    node.save()
                    print "!!## -- NODE: %s SAVED -- ##!!" % node
                    print "!!## -- NEW RUN LIST: %s" % node.run_list
                    print "!!## -- NEW ENVIRONMENT: %s" % node.chef_environment
                except Exception, e:
                    print "!!## -- Failed to save node -- Exception: %s -- ##!!" % e
                
