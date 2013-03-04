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

def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 'retrun': None, 'exception': cpe}

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
                platform_family = node['platform_family']
                
                if display_only:
                    print "!!## -- Role %s found, would remove chef on %s with ip %s -- ##!!" % (results.role, node, ip)
                else:
                    to_run_list.append({'node': node, 'ip': ip, 'root_password': root_password, 'platform_family': platform_family})

    if not display_only:
        failed_runs = 0
        for server in to_run_list:
            if server['platform_family'] == 'debian':
                remote_return = run_remote_ssh_cmd(server['ip'], 'root', server['root_password'], 'apt-get remove --purge -y chef; rm -rf /etc/chef')
            elif server['platform_family'] == 'rhel':
                remote_return = run_remote_ssh_cmd(server['ip'], 'root', server['root_password'], 'yum remove -y chef; rm -rf /etc/chef /var/chef')
            else:
                print "!!## -- Server has a unsupported OS...try again later --##!!"
                failed_runs += 1

            if remote_return is not None:
                if remote_return['success']:
                    print "Successfully removed chef from server with ip: %s" % ip
                else:
                    print "Failed to remove chef from server with ip: %s" % ip
                    print "!!## -- Return Code: %s -- ##!!" % remote_return['exception'].returncode
                    # This print will print the password, use it wisely (jacob).
                    #print "!!## -- Command: %s -- ##!!" % remote_return['exception'].cmd
                    print "!!## -- Output: %s -- ##!!" % remote_return['exception'].output
                    failed_runs += 1

        if failed_runs > 0:
            sys.exit(1)
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!" % policy
    sys.exit(1)
