#!/usr/bin/python
import os
import sys
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server.")

parser.add_argument('--policy', action="store", dest="policy", default="qa-opencenter-server", required=True, 
                    help="Razor policy to use.")

parser.add_argument('--role', action="store", dest="role", required=True, help="Chef role to install opencenter server on.")

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.4:4000", required=False, help="Url for chef server.")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef.")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem", required=False,                help="Location of the chef client pem file.")

parser.add_argument('--oc_install_url', action="store", dest="oc_install_url", required=True, 
                    help="The location of the install server script for OpenCenter.")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, 
                    help="Debug vs Run.")

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

#Collect active models that match the given policy.
razor = razor_api(results.razor_ip)
policy = results.policy

print "!!## -- Attempting to install opencenter server for role %s -- ##!!" % results.role
print "!!## -- Display only: %s " % results.display_only

# Gather the active models from Razor for the given policy.
active_models = razor.simple_active_models(policy)
to_run_list = []

# If we have active models for the policy, continue...
if active_models:
    for active in active_models:
        # Save information from each server that we will need.
        data = active_models[active]
        chef_name = get_chef_name(data)
        root_password = get_root_pass(data)

        with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
            node = Node(chef_name)

            # if the chef role for the server matches our given role, gather info.
            if 'role[%s]' % results.role in node.run_list:
                ip = node['ipaddress']

                # debug vs. run.
                if display_only:
                    print "!!## -- Role %s found, would install OpenCenter server on %s with ip %s --##!!" % (results.role, node, ip)
                else:
                    # save the server and its info to the run list.
                    to_run_list.append({'node': node, 'ip': ip, 'root_password': root_password})

    if not display_only and to_run_list:
        failure = False
        for server in to_run_list:
            print "!!## -- Attempting to install OpenCenter server on %s with ip %s --##!!" % (server['node'], server['ip'])
            try:
                # run the command to install opencenter server.
                check_call_return = check_call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'curl -L \"%s\" | bash'" % (server['root_password'], server['ip'], results.oc_install_url), shell=True)
                print "!!## -- Sucessfully installed OpenCenter server on server with ip: %s --##!!" % server['ip']
            except CalledProcessError, cpe:
                print "!!## -- Failed to install OpenCenter server on server with ip: %s --##!!" % server['ip']
                print "!!## -- Return Code: %s -- ##!!" % cpe.returncode
                #print "!!## -- Command: %s -- ##!!" % cpe.cmd
                print "!!## -- Output: %s -- ##!!" % cpe.output
                failure = True
        if failure:
            print "!!## -- One or more servers failed to install...check logs --##!!"
            sys.exit(1)
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)
