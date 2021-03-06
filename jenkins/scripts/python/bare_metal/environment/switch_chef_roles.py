#!/usr/bin/python
import os
import sys
import json
import argparse
from chef import *
from razor_api import razor_api

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", required=True, help="Razor policy to set chef roles for.")

parser.add_argument('--chef_environment', action="store", dest="chef_environment", required=False, help="Environment to switch roles for")

parser.add_argument('--roles_location', action="store", dest="roles_location", required=True, 
                    help="Location of the roles list json file for the environment")

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.4:4000", required=False, 
                    help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem", 
                    required=True, help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=True, 
                    help="Display the node information only (will not reboot or teardown am)")

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

#############################################################
#Collect active models that match policy from given input
#############################################################

razor = razor_api(results.razor_ip)
policy = results.policy

if results.chef_environment is not None:
    chef_environment = results.chef_environment
else:
    chef_environment = policy

# Open the role list json file
try:
    # Open the file
    fo = open("%s" % results.roles_location, "r")
except IOError:
    print "!!## -- Failed to open file %s, exiting script -- ##!!" % results.roles_location
    sys.exit(1)
else:
    # read the json in
    temp_roles = json.loads(fo.read())

    #close the file
    fo.close()

    # print message for debugging
    print "!!## -- %s successfully read and closed -- ##!!" % results.roles_location

print "!!## -- Switching roles for  '%s'  active models -- ##!!" % policy
print "!!## -- Display only: %s -- ##!!" % results.display_only

# create the roles list from the ordered json
roles = []
for i in range(len(temp_roles)):
    roles.append(temp_roles['%s' % i])

# Gather the active models with the policy from the cmd line
active_models = razor.simple_active_models(policy)

if active_models:
    # Gather all of the active models for the policy and get information about them
    i = 0
    for active in active_models:
        data = active_models[active]
        chef_name = get_chef_name(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)
            run_list = node.run_list
            environment = node.chef_environment
            
            if display_only:
                if (i > len(roles) - 1):
                    i = len(roles) - 1
                print "!!## -- %s has run list: %s, and environment: %s -- ##!!" % (node, run_list, environment)
                print "!!## -- %s run list will be switched to %s with environment %s -- ##!!" % (node, roles[i], policy)
                i += 1
            else:
                # set the environment
                print "!!## -- %s has environment: %s -- ##!!" % (node, environment)
                
                if environment != chef_environment:
                    environment = chef_environment
                    try:
                        node.chef_environment = environment
                        node.save()
                        print "!!## -- NODE: %s SAVED WITH NEW ENVIRONMENT: %s -- ##!!" % (node, node.chef_environment)
                    except Exception, e:
                        print "!!## -- Failed to save node environment -- Exception: %s -- ##!!" % e
                        sys.exit(1)
                else:
                    print "!!## -- Node %s already had the correct environment, no change" % node
                
                # This sets the last X amount of boxes to the last role in the role list
                if (i >= len(roles) - 1):
                    i = len(roles) - 1

                # If the role isnt already set, set it
                if roles[i] not in run_list:
                    
                    print "!!## -- %s run list will be switched to %s -- ##!!" % (node, roles[i])
                    run_list = roles[i]

                    try:
                        # save the new run list
                        node.run_list = run_list
                        node.save()
                        print "!!## -- NODE: %s SAVED WITH NEW RUN LIST %s -- ##!!" % (node, node.run_list)
                    except Exception, e:
                        print "!!## -- Failed to save node -- Exception: %s -- ##!!" % e
                        sys.exit(1)
                else:
                    print "!!## -- %s already has the proper run list, not changing -- ##!!" % node

                i += 1
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)
