#!/usr/bin/python
import os
import sys
import json
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP of the Razor server")

parser.add_argument('--policy', action="store", dest="policy", default="qa-opencenter-client", required=True, 
                    help="Razor policy name to install against.")

parser.add_argument('--role', action="store", dest="role", required=True, default="qa-opencenter-dashboard", help="Chef Role to install against")

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.4:4000", required=False, 
                    help="URL of the chef server.")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="Client in chef to run as.")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem", required=False,                help="chef_client pem file location")

parser.add_argument('--oc_install_url', action="store", dest="oc_install_url", required=True, 
                    help="The location of the client install script for OpenCenter")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, 
                    help="Run vs Debug.")

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

print "!!## -- Attempting to install opencenter dashboard for role %s --##!!" % results.role
print "!!## -- Display only: %s  -- ##!!" % results.display_only

# Gather the active models from Razor for the given policy
active_models = razor.simple_active_models(policy)
to_run_list = []

if active_models:
    # When we come across our OpenCenter Server in the roles, save its ip
    opencenter_server_ip = ''

     # Gather all of the active models for the policy and get information about them
    for active in active_models:
        data = active_models[active]
        chef_name = get_chef_name(data)
        root_password = get_root_pass(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            # Get the node with the chef name we are looking for.
            node = Node(chef_name)
            
            # If the run list for the node is a opencenter server, save its ip.
            if 'role[qa-opencenter-server]' in node.run_list:
                opencenter_server_ip = node['ipaddress']

            # if the role for the server is the role we are looking for, save its ip and add it to the run list.
            if 'role[%s]' % results.role in node.run_list:
                # save the servers ip
                ip = node['ipaddress']
            
                # debug print vs. run
                if display_only:
                    print "!!## -- Role %s found,  would install opencenter dashboard on %s with ip %s -- ##!!" % (results.role, node, ip)
                else:
                    # save the server to our run list
                    to_run_list.append({'node': node, 'ip': ip, 'root_password': root_password})
    
    # if we are not in debug, check the length of the run list and run the subprocesses to install oc client.
    if not display_only and to_run_list:
        failure = False

        # Loop through the servers in the run list and install opencenter client.
        for server in to_run_list:
            print "!!## -- Attempting to install opencenter dashboard on %s with ip %s -- ##!!" % (server['node'], server['ip'])
            try:
                check_call_return = check_call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'curl -L \"%s\" | bash -s dashboard %s'" % (server['root_password'], server['ip'], results.oc_install_url, opencenter_server_ip), shell=True)
                print "!!## -- OpenCenter dashboard installed sucessfully on server with ip %s -- ##!!" % server['ip']
            except CalledProcessError, cpe:
                print "!!## -- Failed to install OpenCenter dashboard on server with ip: %s --##!!" % server['ip']
                print "!!## -- Return Code: %s -- ##!!" % cpe.returncode
                #print "!!## -- Command: %s -- ##!!" % cpe.cmd
                print "!!## -- Output: %s -- ##!!" % cpe.output
                failure = True
        if failure:
            print "!!## -- One or more of the opencenter dashboards failed, check logs -- ##!!"
            sys.exit(1)
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)