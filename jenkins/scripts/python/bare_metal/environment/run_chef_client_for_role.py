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
print " Switching roles and running chef-client for  '%s'  active models" % policy
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
     for active in active_models:
          data = active_models[active]
          chef_name = get_chef_name(data)
          root_password = get_root_pass(data)

          with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
               node = Node(chef_name)

               if 'role[%s]' % results.role in node.run_list:
                    ip = node['ipaddress']
               
                    if results.display_only == 'true':
                         print "!!## -- ROLE %s FOUND, would run chef-client on %s with ip %s..." % (results.role, node, ip)
                    else:
                         print "!!## -- ROLE %s FOUND, runnning chef-client on %s with ip %s..." % (results.role, node, ip)
                         to_run_list.append({'node': node, 'ip': ip, 'root_password': root_password})

     if results.display_only == 'false':
          for server in to_run_list:
               print "Trying chef-client on %s with ip %s...." % (server['node'], server['ip'])
               try:
                    subprocess.call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'chef-client'" % (server['root_password'], server['ip']), shell=True)
                    print "chef-client success..."
               except Exception, e:
                    print "chef-client FAILURE: %s " % e