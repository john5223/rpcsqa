#!/usr/bin/python
import os
import sys
import json
import argparse
import subprocess
from chef import *
from razor_api import razor_api

parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", required=True, help="Razor policy to set chef roles for.")

parser.add_argument('--role', action="store", dest="role", required=True, help="Chef role to run chef-client on")

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.4:4000", required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem",
                    required=False, help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, 
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
print " Attempting to run chef-client for role %s " % results.role
print "Display only: %s " % results.display_only

active_models = razor.simple_active_models(policy)
to_run_list = []

if active_models:
    # Gather all of the active models for the policy and get information about them
    for am in active_models:
        data = active_models[am]
        chef_name = get_chef_name(data)
        root_password = get_root_pass(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)

            if 'role[%s]' % results.role in node.run_list:
                ip = node['ipaddress']
                platform_family = node['platform_family']

                if display_only:
                    print "!!## -- ROLE %s FOUND, would run chef-client on %s with ip %s..." % (results.role, node, ip)
                else:
                    print "!!## -- ROLE %s FOUND, runnning chef-client on %s with ip %s..." % (results.role, node, ip)

                    # append the server to the to run list
                    to_run_list.append({'node': node, 'ip': ip, 'root_password': root_password, 'platform_family': platform_family})

    if not display_only and to_run_list:
        for server in to_run_list:
            print "Trying chef-client on %s with ip %s...." % (server['node'], server['ip'])
            try:
                return_code = subprocess.call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'chef-client;chef-client'" % (server['root_password'], server['ip']), shell=True)
                if return_code == 0:
                    print "chef-client success..."
                else:
                    print "chef-client failed..."
                    sys.exit(1)
            except Exception, e:
                print "chef-client FAILURE: %s " % e
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)


# Only need to comment out require tty on rhel
# Moved to bottom as it is not needed anymore but I dont want to delete it
# TODO (jacob) : move this to kickstart???
"""
if server['platform_family'] == 'rhel':
    print "Commenting out requiretty..."
    try:
        sed_regex = "s/^Defaults[ \\t]+requiretty/#Defaults requiretty/g"
        sed_string = "sed -i -E \'%s\' /etc/sudoers" % sed_regex
        print "SED STRING: %s" % sed_string
        return_code = subprocess.check_output("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s \"%s\"" % (server['root_password'], server['ip'], sed_string), stderr=subprocess.STDOUT, shell=True)
        print "Successfully commented out requiretty..."
    except Exception, e:
        print "Failed to comment out requiretty..."
        print "Command: %s" % e.cmd
        print "Return Code: %s..." % e.returncode
        print "Output: %s..." % e.output
        sys.exit(1)
"""