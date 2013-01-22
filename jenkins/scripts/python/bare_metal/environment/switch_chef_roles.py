#!/usr/bin/python
import os
import sys
import json
import argparse
from razor_api import razor_api
import time
#from chef import *


parser = argparse.ArgumentParser()
# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Razor policy to set chef roles for.")

parser.add_argument('--roles_location', action="store", dest="roles_location", 
                    required=True, help="Location of the roles list json file for the environment")

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

# Open the role list json file
try:
    # Open the file
    fo = open("%s" % results.roles_location, "r")
except IOError:
    print "Failed to open file %s, exiting script" % results.roles_location
    sys.exit()
else:
    # read the json in
    roles = json.loads(fo.read())
    print json.dumps(roles, indent=4)

    #close the file
    fo.close()

    # print message for debugging
    print "%s successfully read and closed" % results.roles_location

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
            environment = node.chef_environment
            
            if results.display_only == 'true':
                if (i > len(roles) - 1):
                    i = len(roles) - 1
                print "!!## -- "
                print "!!## -- %s has run list: %s, and environment: %s -- ##!!" % (node, run_list, environment)
                print "!!## -- %s run list will be switched to %s with environment %s -- ##!!" % (node, roles[i], policy)
                i += 1
            else:
                # set the environment and run lists
                # this is for our QA environment of 4 servers (2 api, 2 compute), might make script take roles -> numbers at a later date
                print "!!## --   "
                print "!!## -- %s has run list: %s, and environment: %s -- ##!!" % (node, run_list, environment)
                environment = policy
                if (i >= len(roles) - 1):
                    i = len(roles) - 1

                print "!!## -- "
                print "!!## -- %s has run list: %s, and environment: %s -- ##!!" % (node, run_list, environment)
                print "!!## -- %s run list will be switched to %s with environment %s -- ##!!" % (node, roles[i], policy)

                # If the role isnt already set, set it
                if roles[i] not in run_list:
                    run_list = [roles[i]]
                i += 1

                # save the new run list and environment
                node.run_list = run_list
                node.chef_environment = environment

                try:
                    node.save()
                    print "!!## -- NODE: %s SAVED -- ##!!" % node
                    print "!!## -- NEW RUN LIST: %s" % node.run_list
                    print "!!## -- NEW ENVIRONMENT: %s" % node.chef_environment
                except Exception, e:
                    print "!!## -- Failed to save node -- Exception: %s -- ##!!" % e
