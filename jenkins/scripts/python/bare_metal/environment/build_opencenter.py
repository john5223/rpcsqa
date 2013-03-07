#!/usr/bin/python
import os
import sys
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
parser.add_argument('--cluster_size', action="store", dest="cluster_size", required=False, default=1, 
                    help="Amount of boxes to pull from active_models")
parser.add_argument('--os', action="store", dest="os", required=False, default='ubuntu', 
                    help="Operating System to use for opencenter")

parser.add_argument('--repo_url', action="store", dest="repo", required=False, 
                    default="https://raw.github.com/rcbops/opencenter-install-scripts/master/install.sh", 
                    help="Operating System to use for opencenter")

parser.add_argument('--action', action="store", dest="action", required=False, 
                    default="build", 
                    help="Action to do for opencenter (build/destroy)")


#Defaulted arguments

parser.add_argument('--razor_ip', action="store", dest="razor_ip", default="198.101.133.3",
                    help="IP for the Razor server")
parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.3:4000", required=False, 
                    help="client for chef")
parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, 
                    help="client for chef")
parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="~/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

parser.add_argument('--clear_pool', action="store", dest="clear_pool", default=True, required=False)
# Save the parsed arguments
results = parser.parse_args()
results.chef_client_pem = results.chef_client_pem.replace('~',os.getenv("HOME"))



def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 'retrun': None, 'exception': cpe, 'command': command}

def remove_broker_fail(policy):
    active_models = razor.simple_active_models(policy)    
    for active in active_models:
        data = active_models[active]
        if 'broker_fail' in data['current_state']:
            print "!!## -- Removing active model  (broker_fail) -- ##!!"
            root_pass = razor.get_active_model_pass(data['am_uuid'])['password']
            ip = data['eth1_ip']
            run = run_remote_ssh_cmd(ip, 'root', root_pass, 'reboot 0')
            if run['success']:
               delete = razor.remove_active_model(data['am_uuid'])
               time.sleep(15)
            else:
                print "Trouble removing broker fail"  
                print run              
                sys.exit(1)
               
def run_chef_client(name,logfile="STDOUT"):
    node = Node(name)    
    ip = node['ipaddress']
    root_pass = razor.get_active_model_pass(node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    return run_remote_ssh_cmd(ip, 'root', root_pass, 'chef-client --logfile %s' % logfile)
       

def remove_chef(name):
    try:
        node = Node(name)
        am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
        root_pass = razor.get_active_model_pass(am_uuid)['password']        
        print "removing chef on %s..." % name
        command = ""
        if node['platform_family'] == "debian":
            command = "apt-get remove --purge -y chef; rm -rf /etc/chef"
        elif node['platform_family'] == "rhel":
            command = 'yum remove --purge -y chef; rm -rf /etc/chef /var/chef'  
        #print command          
        run = run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, command)
    except:
        "Error removing chef"
        sys.exit(1)
    
def erase_node(name):
    print "Deleting: %s" % (name)
    node = Node(name)  
    am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
    run = run_remote_ssh_cmd(node['ipaddress'], 'root', razor.get_active_model_pass(am_uuid)['password'], "reboot 0")
    if not run['success']:
        print "Error rebooting server"
        sys.exit(1)        
    #Knife node remove; knife client remove
    Client(name).delete()
    Node(name).delete()                
    #Remove active model          
    razor.remove_active_model(am_uuid)                            
    time.sleep(15)      



def install_opencenter(server, install_script, type, server_ip=""):
    node = Node(server)
    root_pass = razor.get_active_model_pass(node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    print ""
    print ""
    print "*****************************************************"
    print "*****************************************************"
    print "Installing %s..." % type
    print "*****************************************************"
    print "*****************************************************"
    print ""
    print ""
    if type == "server":
        command = "sudo apt-get update -y -qq; curl %s | bash -s %s 0.0.0.0 secrete" % (install_script, type)
    else:
        command = "sudo apt-get update -y -qq; curl %s | bash -s %s %s secrete" % (install_script, type, server_ip)
    #print "Running: %s " % command
    ret = run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, command)
    if not ret['success']:
        print "Failed to install opencenter %s" % type
        sys.exit(1)






"""
Steps
1. Make an environment for {{name}}-{{os}}-opencenter
2. Grab (cluster_size) amount of active models and change their env to {{name}}-{{os}}-opencenter
3. Remove chef from all boxes
4. Pick one for server and install opencenter-server
5. Install opencenter-agent on the rest of the boxes. 
"""
with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)
    
    
    #Remove broker fails from qa-ubuntu-pool
    remove_broker_fail("qa-ubuntu-pool")
    remove_broker_fail("qa-centos-pool")
            
    env = "%s-%s-opencenter" % (results.name, results.os)
    if not Search("environment").query("name:%s"%env):
        print "Making environment: %s " % env
        Environment.create(env)
   
    cluster_size = int(results.cluster_size)
    
    ############################
    #Prepare environment
    ###########################
    
    nodes = Search('node').query("name:qa-%s-pool*" % results.os)
    #Make sure all networking interfacing is set
    
    for n in nodes:
        node = Node(n['name'])        
        if "recipe[network-interfaces]" not in node.run_list:
            node.run_list = "recipe[network-interfaces]"
            node.save()
            print "Running network interfaces for %s" % node.name
            #Run chef client twice
            run = run_chef_client(node.name, logfile="/dev/null")
            run = run_chef_client(node.name, logfile="/dev/null")
            run = run_chef_client(node.name, logfile="/dev/null")            
            if run['success']:
                print "Done running chef-client"
            else:
                print "Error running chef client for network interfaces"
                print run
                sys.exit(1)
   
    if results.clear_pool:        
        for n in nodes:    
            name = n['name']  
            node = Node(name)      
            if node.chef_environment != "_default":                     
                if (results.action == "destroy" and results.name == "all"):
                    erase_node(name)
                else:                              
                    if node.chef_environment == env:                                    
                        erase_node(name)
                
            
    ######################################################
    ## Collect environment and install opencenter
    ######################################################
    
    if results.action == "build":
        #Collect the amount of servers we need for the opencenter install   
        nodes = Search('node').query("name:qa-%s-pool*" % results.os)          
        if len(nodes) < cluster_size:
            print "*****************************************************"
            print "Not enough nodes for the cluster_size given: %s " % cluster_size
            print "*****************************************************"
            sys.exit(1)
        count = 0    
        opencenter_list = []
        for n in nodes:
            name = n['name']
            node = Node(name)        
            
            if node.chef_environment == "_default" and "recipe[network-interfaces]" in node.run_list:
                node['in_use'] = 1
                node.chef_environment = env
                node.save()
                opencenter_list.append(name)
                print "Taking node: %s" % name    
                count += 1
                if count >= cluster_size:
                    break      
                    
        if not opencenter_list:
            print "No nodes"
            sys.exit(1)
        
        #Remove chef on all nodes
        for n in opencenter_list:
            remove_chef(n)
        
        #Pick an opencenter server, and rest for agents
        server = opencenter_list[0]
        dashboard = []
        clients = []
        if len(opencenter_list) > 1:
            dashboard = opencenter_list[1]
        if len(opencenter_list) > 2:
            clients = opencenter_list[2:]
        
        #Remove chef client...install opencenter server
        print "Making %s the server node" % server
        server_node = Node(server)
        server_ip = server_node['ipaddress']
        server_node['in_use'] = "server"
        install_opencenter(server, results.repo, 'server')
        
        if dashboard:
            Node(dashboard)['in_use'] = "dashboard"
            install_opencenter(dashboard, results.repo, 'dashboard', server_ip)    
        
        for client in clients:
            Node(client)['in_use'] = "agent"
            install_opencenter(client, results.repo, 'agent', server_ip)
    
    
        print ""
        print ""
        print ""
        print ""
        
        print "********************************************************************"
        print "Server: %s - %s  " % (server, server_ip)
        print "Dashboard: %s - https://%s " % (dashboard, Node(dashboard)['ipaddress'])
        for a in clients:
            node = Node(a)
            print "Agent: %s - %s " % (a, node['ipaddress'])
        print "********************************************************************"
         
        print ""
        print ""
        print ""
        print ""
         
         
        