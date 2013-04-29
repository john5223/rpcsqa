#!/usr/bin/python
import os
import sys
import time
import json
import requests
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

"""
This script will automatically build a OpenCenter cluster based on passed parameters
@param name         Name of the cluster
@param cluster_size Size of the cluster
@param server_vms   Whether or not to install OpenCenter Server and Chef Server on VM's on the Controller node
@param os           The operating system to install on (Ubuntu, Centos)
@param repo_url     The URL of the OpenCenter install script
@param action       What to do with the cluster (build, destroy)
"""

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()
parser.add_argument('--name', action="store", dest="name", required=False, default="test", 
                    help="This will be the name for the opencenter chef environment")

parser.add_argument('--cluster_size', action="store", dest="cluster_size", required=False, default=1, 
                    help="Size of the OpenCenter cluster to build")

parser.add_argument('--server_vms', action="store_true", dest="server_vms", required=False, default=False, 
                    help="Whether or not to install opencenter server and chef server on vms on the controller")

parser.add_argument('--os', action="store", dest="os", required=False, default='ubuntu', 
                    help="Operating System to use for opencenter")

parser.add_argument('--repo_url', action="store", dest="repo", required=False, 
                    default="https://raw.github.com/rcbops/opencenter-install-scripts/sprint/install-dev.sh", 
                    help="URL of the OpenCenter install scripts")

parser.add_argument('--action', action="store", dest="action", required=False, default="build", 
                    help="Action to do for opencenter (build/destroy)")

#Defaulted arguments
parser.add_argument('--razor_ip', action="store", dest="razor_ip", default="198.101.133.3",
                    help="IP for the Razor server")
parser.add_argument('--chef_url', action="store", dest="chef_url", default="https://198.101.133.3:443", required=False, 
                    help="URL of the chef server")
parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, 
                    help="client for chef")
parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="~/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

parser.add_argument('--clear_pool', action="store_true", dest="clear_pool", default=True, required=False)

# Save the parsed arguments
results = parser.parse_args()
results.chef_client_pem = results.chef_client_pem.replace('~',os.getenv("HOME"))

def cleanup_environment(chef_environment):
    nodes = Search('node').query("chef_environment:%s AND NOT in_use:0") % chef_environment
    for n in nodes:
        erase_node(n)

def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 'return': None, 'exception': cpe, 'command': command}

def run_remote_scp_cmd(server_ip, user, password, to_copy):
    command = "sshpass -p %s scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet %s %s@%s:~/" % (password, to_copy, user, server_ip)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 
                'return': ret, 
                'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 
                'return': None, 
                'exception': cpe, 
                'command': command}

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
               
def run_chef_client(name, logfile="STDOUT"):
    node = Node(name)    
    ip = node.attributes['ipaddress']
    root_pass = razor.get_active_model_pass(node.attributes['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
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
            command = 'yum remove -y chef; rm -rf /etc/chef /var/chef'  
        #print command          
        run = run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, command)
    except:
        print "Error removing chef"
        sys.exit(1)
    
def erase_node(name):
    print "Deleting: %s" % (name)
    node = Node(name)  
    am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
    run = run_remote_ssh_cmd(node['ipaddress'], 'root', razor.get_active_model_pass(am_uuid)['password'], "reboot 0")
    if not run['success']:
        print "Error rebooting server %s " % node['ipaddress']
        sys.exit(1)        
    #Knife node remove; knife client remove
    Client(name).delete()
    Node(name).delete()                
    #Remove active model          
    razor.remove_active_model(am_uuid)                            
    time.sleep(15)      

def install_opencenter(server, install_script, role, server_ip="0.0.0.0"):
    node = Node(server)
    root_pass = razor.get_active_model_pass(node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    print ""
    print ""
    print "*****************************************************"
    print "*****************************************************"
    print "Installing %s..." % role
    print "*****************************************************"
    print "*****************************************************"
    print ""
    print ""
    #if role == "server":
    #    command = "sudo apt-get update -y -qq; curl %s | bash -s %s 0.0.0.0 secrete" % (install_script, role)
    #else:
    #    command = "sudo apt-get update -y -qq; curl %s | bash -s %s %s secrete" % (install_script, role, server_ip)
    if node['platform_family'] == "debian":
        run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, 'apt-get update -y -qq')
    elif node['platform_family'] == "rhel":
        run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, 'yum update -y -q; /etc/init.d/iptables save; /etc/init.d/iptables stop')
    command = "bash <(curl %s) --role=%s --ip=%s" % (install_script, role, server_ip)
    print command
    #print "Running: %s " % command
    ret = run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, command)
    if not ret['success']:
        print "Failed to install opencenter %s" % type
        sys.exit(1)

def install_opencenter_vm(vm_ip, oc_server_ip, install_script, role, user, password):
    command = "bash <(curl %s) --role=%s --ip=%s" % (install_script, role, oc_server_ip)
    install_run = run_remote_ssh_cmd(vm_ip, user, password, command)
    if not install_run['success']:
        print "Failed to install OpenCenter %s on VM..." % role
        print "Return Code: %s" % install_run['exception'].returncode
        print "Exception: %s" % install_run['exception']
        sys.exit(1)
    else:
        print "OpenCenter %s successfully installed on vm with ip %s..." % (role, vm_ip)

def prepare_vm_host(controller_node):
    controller_ip = controller_node['ipaddress']
    root_pass = razor.get_active_model_pass(controller_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']

    if controller_node['platform_family'] == 'debian':
        commands = ["aptitude install -y curl dsh screen vim iptables-persistent libvirt-bin python-libvirt qemu-kvm guestfish git",
                    "aptitude update -y",
                    "update-guestfs-appliance",
                    "ssh-keygen -f /root/.ssh/id_rsa -N \"\""]
    else:
        commands = ["yum install -y curl dsh screen vim iptables-persistent libvirt-bin python-libvirt qemu-kvm guestfish git",
                    "yum update -y",
                    "update-guestfs-appliance",
                    "ssh-keygen -f /root/.ssh/id_rsa -N \"\""]

    for command in commands:
        print "Prepare command to run: %s" % command
        prepare_run = run_remote_ssh_cmd(controller_ip, 'root', root_pass, command)
    
        if not prepare_run['success']:
            print "Failed to run command %s, please check the server %s @ ip: %s for errors..." % (command, controller_node, controller_ip)
            print "Return Code: %s" % prepare_run['exception'].returncode
            print "Exception: %s" % prepare_run['exception']
            sys.exit(1)

def clone_git_repo(chef_node, github_user, github_user_pass):
    controller_ip = chef_node['ipaddress']
    root_pass = razor.get_active_model_pass(chef_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    
    # Download vm setup script on controller node.
    print "Cloning repo with setup script..."
    command = "mkdir -p /opt/rpcs; git clone https://%s:%s@github.com/rsoprivatecloud/scripts /opt/rpcs" % (github_user, github_user_pass)
    download_run = run_remote_ssh_cmd(controller_ip, 'root', root_pass, command)
    if not download_run['success']:
        print "Failed to clone script repo on server %s@%s...." % (chef_node, controller_ip)
        print "Return Code: %s" % download_run['exception'].returncode
        print "Exception: %s" % download_run['exception']
        sys.exit(1)
    else:
        print "Successfully cloned repo with setup script..."

def install_server_vms(controller_node, opencenter_server_ip, chef_server_ip, vm_bridge, vm_bridge_device):
    controller_ip = controller_node['ipaddress']
    root_pass = razor.get_active_model_pass(controller_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']

    # Run vm setup script on controller node
    print "Running VM setup script..."
    command = "bash /opt/rpcs/oc_prepare.sh %s %s %s %s" % (chef_server_ip, opencenter_server_ip, vm_bridge, vm_bridge_device)
    print "Prepare command to run: %s" % command
    install_run = run_remote_ssh_cmd(controller_ip, 'root', root_pass, command)
    if not install_run['success']:
        print "Failed to run VM setup script on server %s@%s...." % (controller_node, controller_ip)
        print "Command ran: %s" % install_run['command']
        print "Return Code: %s" % install_run['exception'].returncode
        print "Exception: %s" % install_run['exception']
        sys.exit(1)
    else:
        print "VM's successfully setup on server %s..." % controller_node

def ping_check_vm(ip_address):
    command = "ping -c 5 %s" % ip_address
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False, 'return': None, 'exception': cpe, 'command': command}
    
# If we want vms, assign them ips, these ips are static which means we can only have 1 ubuntu and 1 centos cluster running vms when testing
# We may need to change this later but as this is a matrix for support only 1 cluster testing should be needed.
# Maybe not? If not we need a more clever way of assigning ips to the vms

if results.server_vms:
    vm_bridge = 'ocbr0'
    if results.os == 'ubuntu':
        oc_server_ip = '198.101.133.150'
        chef_server_ip = '198.101.133.151'
        vm_bridge_device = 'eth0'
    else:
        print "%s isnt currently supported for vm deploy, please select Ubuntu" % results.os
        sys.exit(1)
        # !!!When CentOS gets support, turn these on!!!
        # oc_server_ip = '198.101.133.152'
        # chef_server_ip = '198.101.133.153'
        # vm_bridge_device = 'em1'
        

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

    # Remove broker fails for qa-%os-pool
    remove_broker_fail("qa-%s-pool" % results.os)

    # If the environment doesnt exist in chef, make it.
    env = "%s-%s-opencenter" % (results.name, results.os)
    if not Search("environment").query("name:%s"%env):
        print "Making environment: %s " % env
        Environment.create(env)

    # Set the cluster size   
    cluster_size = int(results.cluster_size)
    
    #Prepare environment
    nodes = Search('node').query("name:qa-%s-pool*" % results.os)
    
    #Make sure all networking interfacing is set
    for n in nodes:
        node = Node(n['name'])        
        if "role[qa-base]" in node.run_list:
            node['in_use'] = 0
            node.run_list = ["recipe[network-interfaces]"]
            node.save()
            print "Running network interfaces for %s" % node.name
            
            #Run chef client thrice
            run = run_chef_client(node.name, logfile="/dev/null")
            run = run_chef_client(node.name, logfile="/dev/null")
            run = run_chef_client(node.name, logfile="/dev/null")

            if run['success']:
                print "Done running chef-client"
            else:
                print "Error running chef client for network interfaces"
                print run
                sys.exit(1)

    # If we want to clear the pool
    if results.clear_pool:        
        for n in nodes:    
            name = n['name']  
            node = Node(name)
            if node.chef_environment != "_default" and 'in_use' in node.attributes and node['in_use'] != 0:                     
                if (results.action == "destroy" and results.name == "all"):
                    erase_node(name)
                else:                              
                    if node.chef_environment == env:                                    
                        erase_node(name)
            else:
                node.chef_environment = "_default"
                node.save()
                     
    # Collect environment and install opencenter.
    if results.action == "build":

        #Collect the amount of servers we need for the opencenter install   
        nodes = Search('node').query("name:qa-%s-pool* AND chef_environment:_default" % results.os)          
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

        # Install chef and opencenter on vms on the controller
        if results.server_vms:
            # Set the controller and compute lists
            controller = opencenter_list[0]
            computes = opencenter_list[1:]

            # Check to make sure the VMs ips dont ping
            # Ping the opencenter vm
            oc_ping = ping_check_vm(oc_server_ip)
            if oc_ping['success']:
                print "OpenCenter VM pinged, please tear down old vms before proceeding...."
                sys.exit(1)

            # Ping the chef server vm
            cf_ping = ping_check_vm(chef_server_ip)
            if oc_ping['success']:
                print "Chef Server VM pinged, please tear down old vms before proceeding...."
                sys.exit(1)

            # Open file containing vm login info, load into variable
            try:
                # Open the file
                fo = open("/var/lib/jenkins/source_files/vminfo.json", "r")
            except IOError:
                print "Failed to open /var/lib/jenkins/source_files/vminfo.json"
                sys.exit(1)
            else:
                # Write the json string
                vminfo = json.loads(fo.read())

                #close the file
                fo.close()

                # print message for debugging
                print "/var/lib/jenkins/source_files/vminfo.json successfully open, read, and closed."

            # Edit the controller in our chef
            controller_node = Node(controller)
            controller_node['in_use'] = 'controller_with_vms'
            controller_ip = controller_node['ipaddress']
            controller_node.save()

            #Remove chef on controller
            remove_chef(controller)

            # Prepare the server by installing needed packages
            print "Preparing the VM host server"
            prepare_vm_host(controller_node)

            # Get github user info
            github_user = vminfo['github_info']['user']
            github_user_pass = vminfo['github_info']['password']
            
            # Clone Repo onto controller
            print "Cloning setup script repo onto %s" % controller_node
            clone_git_repo(controller_node, github_user, github_user_pass)

            # install the server vms and ping check them
            print "Setting up VMs on the host server"
            install_server_vms(controller_node, oc_server_ip, chef_server_ip, vm_bridge, vm_bridge_device)
            
            # Need to sleep for 30 seconds to let virsh completely finish
            print "Sleeping for 30 seconds to let VM's complete..."
            time.sleep(30)

            # Ping the opencenter vm
            oc_ping = ping_check_vm(oc_server_ip)
            if not oc_ping['success']:
                print "OpenCenter VM failed to ping..."
                print "Return Code: %s" % oc_ping['exception'].returncode
                print "Output: %s" % oc_ping['exception'].output
                sys.exit(1)
            else:
                print "OpenCenter Server VM set up and pinging..."

            # Ping the chef server vm
            cf_ping = ping_check_vm(chef_server_ip)
            if not cf_ping['success']:
                print "OpenCenter VM failed to ping..."
                print "Return Code: %s" % cf_ping['exception'].returncode
                print "Output: %s" % cf_ping['exception'].output
                sys.exit(1)
            else:
                print "Chef Server VM set up and pinging..."

            # Get vm user info
            vm_user = vminfo['user_info']['user']
            vm_user_pass = vminfo['user_info']['password']

            # Install OpenCenter Server / Dashboard on VM
            install_opencenter_vm(oc_server_ip, oc_server_ip, results.repo, 'server', vm_user, vm_user_pass)
            install_opencenter_vm(oc_server_ip, oc_server_ip, results.repo, 'dashboard', vm_user, vm_user_pass)

            # Install OpenCenter Client on Chef VM
            install_opencenter_vm(chef_server_ip, oc_server_ip, results.repo, 'agent', vm_user, vm_user_pass)

            # Install OpenCenter Client on Controller
            install_opencenter(controller, results.repo, 'agent', oc_server_ip)

            # Install OpenCenter Client on Computes
            for client in computes:
                agent_node = Node(client)
                agent_node['in_use'] = "agent"
                agent_node.save()
                remove_chef(client)
                install_opencenter(client, results.repo, 'agent', oc_server_ip)

            # Print Cluster Info
            print "************************************************************"
            print "2 VMs, 1 controller ( VM Host ), %i Agents" % len(computes)
            print "OpenCenter Server (VM) with IP: %s on Host: %s" % (oc_server_ip, controller)
            print "Chef Server (VM) with IP: %s on Host: %s" % (chef_server_ip, controller)
            print "Controller Node: %s with IP: %s" % (controller, controller_ip)
            for agent in computes:
                node = Node(agent)
                print "Agent Node: %s with IP: %s" % (agent, node['ipaddress'])
            print "************************************************************"

        else:
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
            server_node.save()
            
            remove_chef(server)
            install_opencenter(server, results.repo, 'server')
            
            if dashboard:
                dashboard_node = Node(dashboard) 
                dashboard_node['in_use'] = "dashboard"
                dashboard_node.save()
                remove_chef(dashboard)            
                install_opencenter(dashboard, results.repo, 'dashboard', server_ip)    
            
            for client in clients:
                agent_node = Node(client)
                agent_node['in_use'] = "agent"
                agent_node.save()
                remove_chef(client)
                install_opencenter(client, results.repo, 'agent', server_ip)
        
            print ""
            print ""
            print ""
            print ""
            
            dashboard_ip = Node(dashboard)['ipaddress']
            dashboard_url = ""
            try:
                r = requests.get("https://%s" % dashboard_ip, auth=('admin','password'),verify=False)
                dashboard_url = "https://%s" % dashboard_ip
            except:
                dashboard_url = "http://%s:3000" % dashboard_ip
                pass
                    
            print "********************************************************************"
            print "Server: %s - %s  " % (server, server_ip)
            print "Dashboard: %s - %s " % (dashboard, dashboard_url)
            for a in clients:
                node = Node(a)
                print "Agent: %s - %s " % (a, node['ipaddress'])
            print "********************************************************************"
             
            print ""
            print ""
            print ""
            print ""
