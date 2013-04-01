#!/usr/bin/python
import os
import sys
import requests
import time
import argparse
import time
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

"""
This script will tear down razor server based on their chef roles and environments
"""

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()
parser.add_argument('--name', action="store", dest="name", required=False, default="test", 
                    help="This will be the name for the opencenter chef environment")
parser.add_argument('--os', action="store", dest="os", required=False, default='ubuntu', 
                    help="Operating System to use for opencenter")
parser.add_argument('--repo_url', action="store", dest="opencenter_test_repo", required=False, 
                    default="https://github.com/john5223/opencenter-testerator.git", 
                    help="Testing repo for opencenter")

parser.add_argument('--tests', action="store", dest="opencenter_tests", required=False, 
                    default="test_happy_path.py", 
                    help="Tests to run")

parser.add_argument('--HA', action="store", dest="HA", required=False, 
                    default=True, 
                    help="Do HA for openstack controller")

#Defaulted arguments
parser.add_argument('--razor_ip', action="store", dest="razor_ip", default="198.101.133.3",
                    help="IP for the Razor server")
parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.3:4000", required=False, 
                    help="client for chef")
parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, 
                    help="client for chef")
parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="~/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

# Save the parsed arguments
results = parser.parse_args()
results.chef_client_pem = results.chef_client_pem.replace('~',os.getenv("HOME"))
if results.HA == "True":
    results.HA = True
elif results.HA == "False":
    results.HA = False

def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    """Runs a command over an ssh connection"""
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 'retrun': None, 'exception': cpe, 'command': command}

# Load chef and razor apis
with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)
    
    server = []
    dashboard = []
    agents = []
    
    # Make sure environment exists, if not create one
    env = "%s-%s-opencenter" % (results.name, results.os)
    if not Search("environment").query("name:%s"%env):
        print "Making environment: %s " % env
        Environment.create(env)
    
    # Gather the servers in the environment into their roles
    nodes = Search('node').query("name:qa-%s-pool* AND chef_environment:%s" % (results.os, env))
    for n in nodes:
        node = Node(n['name'])
        #print "Found: %s " % node.name
        #print node.attributes['in_use']
        if node.attributes['in_use'] == "server":
            server.append(node.name)
        elif node.attributes['in_use'] == "dashboard":
            dashboard.append(node.name)
        elif node.attributes['in_use'] == "agent":
            agents.append(node.name)
    print "Server: %s " % server
    print "Dashboard: %s " % dashboard
    print "Agents: %s " % agents

    # Make sure we have the servers we need
    if not dashboard or not server:
        print "No dashboard/server found"
        print "Dashboard: %s" % dashboard
        print "Server: %s " % server
        sys.exit(1)
    if results.HA:
        if len(agents) < 3:
            print "!!## -- Not enough agents for openstack HA deployment -- ##!!"
            sys.exit(1)
    elif len(agents) < 2:
        print "!!## -- Not enough agents for openstack deployment -- ##!!"
        sys.exit(1)
    
    dashboard_ip = Node(dashboard[0])['ipaddress']
    server_ip = Node(server[0])['ipaddress']
    
    dashboardagens_url = ""
    user = ""
    password = ""
    
    # Determine if ssl is being used
    try:
        r = requests.get("https://%s" % dashboard_ip, auth=('admin','password'),verify=False)
        print("!!## -- SSL not being used -- ##!!")
        dashboard_url = "https://%s" % dashboard_ip        
        server_url = "https://%s:8443" % server_ip
        user = "admin"
        password = "password"        
    except Exception, e:
        print("!!## -- SSL being used -- ##!!")
        dashboard_url = "http://%s:3000" % dashboard_ip
        server_url = "http://%s:8080" % server_ip
        pass
                
    # Assign rolls for opencenter-testerator
    chef_server = server[0]
    controller = agents[0]
    if results.HA:
        controller = ",".join([controller, agents[1]])
        compute = ",".join(agents[2:])
    else:
        compute = ",".join(agents[1:])

    opencenter_config = \
"""[opencenter]
endpoint_url = %s
instance_server_hostname = %s
instance_chef_hostname = %s
instance_controller_hostname = %s
instance_compute_hostname = %s

user=%s
password=%s


[cluster_data]
libvirt_type = kvm
osops_public = 198.101.133.0/24
osops_mgmt = 198.101.133.0/24
osops_nova = 198.101.133.0/24
nova_public_if = eth0
nova_vm_bridge = br100
nova_dmz_cidr = 172.16.0.0/12
cluster_name = test_cluster
keystone_admin_pw = secrete
nova_vm_fixed_if = eth1
nova_vm_fixed_range = 192.168.200.0/24

""" % (server_url, server[0], chef_server, controller, compute, user, password)
    
    print "\n*******************"
    print "***    CONFIG   ***"
    print "*******************"
    print opencenter_config
    print ""
    print "****** *************"
    
    # Write the config file to a temporary file
    config_file = "opencenter-%s.conf" % results.name
    try:
        with open('/tmp/%s' % config_file, 'w') as fo:
            fo.write(opencenter_config)
            fo.close()
    except Exception, e:
        print "Error writing file"
        print e
        sys.exit(1)

    # Build Commands to run
    commands=["apt-get install git python-pip -y -q", 
              "rm -rf /root/opencenter-testerator",
              "git clone %s" % results.opencenter_test_repo, 
              "pip install -q -r /root/opencenter-testerator/tools/pip-requires",
              "mv /root/%s /root/opencenter-testerator/etc/" % (config_file)]
    for test in results.opencenter_tests.split(","):
        commands.append("export OPENCENTER_CONFIG='%s'; nosetests opencenter-testerator/opencenter/tests/%s -v" % (config_file, test))
        
    # Get password for OpenCenter server
    server_node = Node(server[0])
    opencenter_server_ip = server_node['ipaddress']
    am_uuid = server_node.attributes['razor_metadata']['razor_active_model_uuid']
    opencenter_server_password = razor.get_active_model_pass(am_uuid)['password']

    # Transfer the testerator Config file to the server
    try:
        print "!!## -- Transfering the config file to the server: %s -- ##!!" % opencenter_server_ip
        check_call_return = check_call("sshpass -p %s scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet %s root@%s:/root/%s" % (opencenter_server_password, '/tmp/%s' % config_file, opencenter_server_ip, config_file), shell=True)
    except CalledProcessError, cpe:
        print "!!## -- Failed to transfer environment file  -- ##!!"
        sys.exit(1)   
   
    # Run commands to test
    for command in commands: 
        try:
            check_call_return = check_call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s '%s'" % (opencenter_server_password, opencenter_server_ip, command), shell=True)
            print "!!## -- command: %s on %s run successfully  -- ##!!" % (command, opencenter_server_ip)
        except CalledProcessError, cpe:
            print "!!## -- Command %s failed to run on server with ip: %s -- ##!!" % (command, opencenter_server_ip)
            print "!!## -- Return Code: %s -- ##!!" % cpe.returncode
            #print "!!## -- Command: %s -- ##!!" % cpe.cmd
            print "!!## -- Output: %s -- ##!!" % cpe.output
            sys.exit(1)
