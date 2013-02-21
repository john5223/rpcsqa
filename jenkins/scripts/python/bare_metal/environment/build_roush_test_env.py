#!/usr/bin/python
import os
import sys
import subprocess
import json
import argparse
from razor_api import razor_api
import time
from chef import *
from ssh_session import ssh_session

parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", required=True, help="Razor policy to set chef roles for.")

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.4:4000", required=True, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=True, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem",
                    required=True, help="client pem for chef")
parser.add_argument('--roush_test_repo', action="store", dest="roush_test_repo", default="https://github.com/galstrom21/roush-testerator.git", required=True, 
                    help="URL of Roush Test git repo")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, 
                    help="Display the node information only (will not reboot or teardown am)")

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
print "Display only: %s " % results.display_only

active_models = razor.simple_active_models(policy)
servers = []

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
            run_list = node.run_list
            ip = node['ipaddress']
            # append the server to the to run list
            servers.append({'node': node, 'ip': ip, 'root_password': root_password, 'run_list': run_list})

    if results.display_only == 'false' and len(servers) > 0:
        roush_test_env = {'ROUSH_ENDPOINT': 'http://127.0.0.1:8080'}
        temp = []
        roush_role_list = ['INSTANCE_CHEF_HOSTNAME', 'INSTANCE_COMPUTE_HOSTNAME', 'INSTANCE_CONTROLLER_HOSTNAME']
        roush_server_ip = ""
        roush_server_password = ""
        
        # print json.dumps(servers, indent=4)
        print servers

        for server in servers:
            print server['run_list']
            if 'role[qa-roush-server]' in server['run_list']:
                print "roush server found"
                roush_test_env['INSTANCE_SERVER_HOSTNAME'] = server['node']
                roush_server_ip = server['ip']
                roush_server_password = server['root_password']
            elif 'role[qa-roush-client]' in server['run_list']:
                print "roush client found"
                temp.append(server['node'])
            else:
                pass
                
        for role in roush_role_list:
            roush_test_env['%s' % role] = temp.pop()

        try:
            # Open the file
            fo = open("env.sh", "w")
        except IOError:
            print "Failed to open file env.sh"
        else:
            for k,v in roush_test_env.iteritems():
                to_write = "export %s=%s\n" % (k, v)
                fo.write(to_write)
            fo.close()
            print "env.sh successfully saved"

        session = ssh_session("root", roush_server_ip, roush_server_password, True)
        print session
        session.scp("env.sh", "/root/")
        session.close()
        print "Removing environment from system"
        try:
            os.remove("env.sh")
        except Exception, e:
            print "Failed to remove file: %s" % e
            sys.exit(1)


        print "Running roush tests on %s with ip %s...." % (server['node'], server['ip'])
        commands=["apt-get install git python-pip -y", "git clone %s" % results.roush_test_repo, "cd roush-testerator", "cp /root/env.sh /root/roush-testerator", "source env.sh", "pip install -r /root/roush-testerator/tools/pip-requires", "nosetests /root/roush-testerator/tests/test_happy_path.py"]
        for command in commands:
            try:
                print "running command: %s on %s" % (command, roush_server_ip)
                return_code = subprocess.check_output("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s '%s'" % (roush_server_password, roush_server_ip, command), stderr=subprocess.STDOUT, shell=True)
                print "Successfully ran command %s" % command
            except Exception, e:
                print "Failed to run command %s" % command
                print "Command: %s" % e.cmd
                print "Return Code: %s..." % e.returncode
                print "Output: %s..." % e.output
                sys.exit(1)


