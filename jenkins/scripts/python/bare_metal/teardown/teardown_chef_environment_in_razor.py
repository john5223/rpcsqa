#!/usr/bin/python
import os
import sys
import argparse
import time
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

def get_private_ip(chef_node_addresses):
    #print "!!## -- Addresses: %s -- ##!!" % chef_node_addresses
    for k, v in chef_node_addresses:
        #print "!!## -- Key: %s -- Value: %s -- ##!!" % (k,v)
        for k2, v2 in v.iteritems():
            #print "!!## -- Key2: %s type(%s) -- Value2: %s type(%s) -- ##!!" % (k2, type(k2), v2, type(v2))
            if str(v2) == 'inet':
                #print "!!## -- Private IP: %s -- ##!!" % k
                return k

"""
Steps
1. Gather all the nodes in the given environment
2. Gather all the nodes whos role is not qa based
4. Find the name of the node that has the role
5. Find the active model in razor with the node name found
6. Tear it down ( remove chef node, client, active model, then reboot)
"""
failed_runs = False
with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)
    nodes = Search('node').query("chef_environment:%s" % results.chef_environment)
    
    # Loop through the nodes in the environment and take appropriate action.
    for n in nodes:
        # Gather info about the node
        node = Node(n['name'])
        node_name = n['name']
        node_run_list = node.run_list
        node_ip = node['ipaddress']
        node_am_uuid = node.normal['razor_metadata']['razor_active_model_uuid']
        node_pass = ''

        platform_family = node['platform_family']
        print "!!## -- Node %s has platform_family: %s -- ##!!" % (node_name, platform_family)
        #print "!!## -- Node %s network interfaces: -- ##!!" % node_name
        for interface in node['network']['interfaces']:
            if platform_family == 'debian':
                if 'eth1' in interface:
                    addresses = node['network']['interfaces']['%s' % interface]['addresses'].iteritems()
                    node_private_ip = get_private_ip(addresses)
            elif platform_family == 'rhel':
                if 'em2' in interface:
                    addresses = node['network']['interfaces']['%s' % interface]['addresses'].iteritems()
                    node_private_ip = get_private_ip(addresses)
            else:
                print "Platform not supported..."
        
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
            # Remove the active model from razor
            print "!!## -- Removing active model -- ##!!"
            try:
                delete = razor.remove_active_model(node_am_uuid)
                print "Deleted: %s " % delete
                #pass
            except Exception, e:
                print "!!## -- Error removing active model: %s -- ##!!" % e
                pass

            # Remove the node from chef
            print "!!## -- Removing chef-node -- ##!!"
            try:
                node.delete()
            except Exception, e:
                print "!!## -- Error removing chef node: %s -- ##!!" % e
                failed_runs = True

            # remove the client from chef
            print "!!## -- Removing chef clients..."
            chef_api = ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client)
            try:
                response = chef_api.api_request('DELETE', '/clients/%s' % node_name)
                print "!!## -- Client %s removed with response: %s -- ##!!" % (node_name, response)
            except Exception, e:
                print "!!## -- Error removing chef node: %s -- ##!!" % e
                failed_runs = True
            
            # reboot the server
            print "!!## -- Trying to restart server with ip %s -- ##!!" % node_ip
            remote_return = run_remote_ssh_cmd(node_ip, 'root', node_pass, 'reboot 0')
            if remote_return['success']:
                print "!!## -- Successful restart of server with ip %s -- ##!!" % node_ip
            else:
                remote_return = run_remote_ssh_cmd(node_private_ip, 'root', node_pass, 'reboot 0')
                if remote_return['success']:
                    print "!!## -- Successful restart of server with ip %s -- ##!!" % node_ip
                else:
                    print "!!## -- Failed to restart server with ip: %s -- ##!!" % node_private_ip
                    print "!!## -- Return Code: %s -- ##!!" % remote_return['cpe'].returncode
                    # This print will print the password, use it wisely (jacob).
                    #print "!!## -- Command: %s -- ##!!" % remote_return['cpe'].cmd
                    print "!!## -- Output: %s -- ##!!" % remote_return['cpe'].output
                    failed_runs = True

            # Sleep for 20 seconds
            print "!!## -- Sleeping for 20 seconds -- ##!!"
            time.sleep(20)

if failed_runs:
    print "!!## -- One or more chef-client runs failed...check logs -- ##!!"
    sys.exit(1)
