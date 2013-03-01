#!/usr/bin/python
import os
import sys
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

"""
This script will tear down razor server based on their chef roles and environments
"""

def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 'retrun': None, 'exception': cpe}

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")

parser.add_argument('--chef_environment', action="store", dest="chef_environment", required=True, 
                    help="This will be the environment to look in for Razor active models")

parser.add_argument('--chef_role', action="store", dest="chef_role", required=True, help='The chef role to tear down')

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.3:4000", required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, 
                    help="Display the node information only (will not reboot or teardown am)")

# Save the parsed arguments
results = parser.parse_args()

# converting string display only into boolean
if results.display_only == 'true':
    display_only = True
else:
    display_only = False

"""
Steps
1. Gather all the nodes in the given environment
2. Gather all the nodes whos role is not qa based
4. Find the name of the node that has the role
5. Find the active model in razor with the node name found
6. Tear it down ( remove chef node, client, active model, then reboot)
"""
with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)
    nodes = Search('node').query("chef_environment:%s" % results.chef_environment)
    for n in nodes:
        node = Node(n['name'])
        node_name = n['name']
        node_run_list = node.run_list
        node_ip = node['ipaddress']
        node_am_uuid = node.normal['razor_metadata']['razor_active_model_uuid']
        node_pass = ''
        
        # Get the AM password from Razor
        try:
            passwd = razor.get_active_model_pass(node_am_uuid)
            if passwd['status_code'] == 200:
                node_pass = passwd['password']
            else:
                print "!!## -- Error getting password for active model, exited with error code: %s -- ##!!" % passwd['status_code']
                sys.exit(1)
        except Exception, e:
            print "Error: %s" % e

        # Begin to tear things down
        if display_only:
            print "Node Name: %s" % node_name
            print "IP: %s" % node_ip
            print "run_list: %s" % node_run_list
            print "Active model UUID: %s" % node_am_uuid
        else: 
            print "!!## -- Removing active model -- ##!!"
            try:
                delete = razor.remove_active_model(node_am_uuid)
                print "Deleted: %s " % delete
                #pass
            except Exception, e:
                print "!!## -- Error removing active model: %s -- ##!!" % e
                pass

            print "!!## -- Removing chef-node -- ##!!"
            try:
                node.delete()
            except Exception, e:
                print "!!## -- Error removing chef node: %s -- ##!!" % e
                pass

            print "!!## -- Removing chef clients..."
            try:
                chef_api = ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client)
                if chef_api is not None:
                    response = chef_api.api_request('DELETE', '/clients/%s' % node_name)
                    print "!!## -- Client %s removed with response: %s -- ##!!" % (node_name, response)
                else:
                    pass
            except Exception, e:
                print "!!## -- Error removing chef node: %s -- ##!!" % e
                pass
            
            print "!!## -- Trying to restart server with ip %s -- ##!!" % ip
            try:
                run_remote_ssh_cmd(node_ip, 'root', node_pass, 'reboot 0')
                print "!!## -- Restart of server with ip: %s was a success -- ##!!" % node_ip
            except CalledProcessError, cpe:
                print "!!## -- Failed to restart server -- ##!!"
                print "!!## -- IP: %s -- ##!!" % node_ip
                print "!!## -- Exited with following error status: -- ##!!"
                print "!!## -- Return code: %i -- ##!!" % cpe.returncode
                #print "!!## -- Command: %s -- ##!!" % cpe.cmd
                print "!!## -- Output: %s -- ##!!" % cpe.output
