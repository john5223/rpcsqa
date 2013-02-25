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

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", required=True, help="Razor policy to set chef roles for.")

parser.add_argument('--role', action="store", dest="role", required=True, help="Chef role to run chef-client on")

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.4:4000", required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem", required=False,                help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, help="Display the node information only (                will not reboot or teardown am)")

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

print "!!## -- Attempting to remove chef for role %s -- ##!!" % results.role
print "!!## -- Display only: %s -- ##!!" % results.display_only

active_models = razor.simple_active_models(policy)
to_run_list = []

if active_models:
    # Gather all of the active models for the policy and get information about them
    for active in active_models:
        data = active_models[active]
        chef_name = get_chef_name(data)
        root_password = get_root_pass(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)
            if 'role[%s]' % results.role in node.run_list:
                ip = node['ipaddress']

                if display_only:
                    print "!!## -- Role %s found, would remove chef on %s with ip %s -- ##!!" % (results.role, node, ip)
                else:
                    to_run_list.append({'node': node, 'ip': ip, 'root_password': root_password})

    if not display_only:
        failed_runs = 0
        for server in to_run_list:
            print "!!## -- Trying to remove chef on %s with ip %s -- ##!!" % (server['node'], server['ip'])
            try:
                check_call_return = check_call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'apt-get remove --purge -y chef; rm -rf /etc/chef'" % (server['root_password'], server['ip']), shell=True)
            except CalledProcessError, cpe:
                if cpe.returncode == 100:
                    "!!## -- Chef removal failed...Chef didn't exist on the server -- ##!!"
                else:
                    print "!!## -- Chef removal failed -- ##!!"
                    print "!!## -- Return code: %i -- ##!!" % cpe.returncode
                    print "!!## -- Command: %s -- ##!!" % cpe.cmd
                    print "!!## -- Output: %s -- ##!!" % cpe.output
                    failed_runs += 1

        if failed_runs > 0:
            sys.exit(1)
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)
