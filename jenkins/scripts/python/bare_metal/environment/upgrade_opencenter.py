#!/usr/bin/python
import os
import sys
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()
parser.add_argument('--name', action="store", dest="name", required=False, default="test", 
                    help="This will be the name for the opencenter chef environment")

parser.add_argument('--os', action="store", dest="os", required=False, default='ubuntu', 
                    help="Operating System to use for opencenter")

parser.add_argument('--repo_url', action="store", dest="repo", required=False, 
                    default="http://build.monkeypuppetlabs.com/proposed-packages/rcb-utils", 
                    help="URL of the OpenCenter install scripts")

#Defaulted arguments
parser.add_argument('--razor_ip', action="store", dest="razor_ip", default="198.101.133.3",
                    help="IP for the Razor server")
parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.3:4000", required=False, 
                    help="URL of the chef server")
parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, 
                    help="client for chef")
parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="~/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

# Save the parsed arguments
results = parser.parse_args()
results.chef_client_pem = results.chef_client_pem.replace('~',os.getenv("HOME"))

def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s \"%s\"" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 'return': None, 'exception': cpe, 'command': command}

"""
Find opencenter agents and upload their packages
"""
with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)
    servers = []
    env = "%s-%s-opencenter" % (results.name, results.os)
    nodes = Search('node').query("name:qa-%s-pool* AND chef_environment:%s" % (results.os, env))
    package = "deb %s precise rcb-utils" % results.repo
    command = \
"""
sed -i 's/(.*)/#\1/g' /etc/apt/sources.list.d/rcb-utils.list
echo '%s' >> /etc/apt/sources.list.d/rcb-utils.list
apt-get update
apt-get upgrade -y
""" % package
    
    print "Running command: %s\n On servers for environment: %s" % (command, env)
    
    for n in nodes:
        node = Node(n['name'])
        password = razor.get_active_model_pass(node.attributes['razor_metadata']['razor_active_model_uuid'])['password']
        run_remote_ssh_cmd(node['ipaddress'], 'root', password, command)
