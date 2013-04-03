#!/usr/bin/python
import os
import requests
import sys
import time
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()
parser.add_argument('--name', action="store", dest="name", required=False, default="glance-cf", 
                    help="This will be the name for the Open Stack chef environment")

parser.add_argument('--cluster_size', action="store", dest="cluster_size", required=False, default=4, 
                    help="Size of the Open Stack cluster.")

parser.add_argument('--ha_enabled', action='store', dest='ha_enabled', required=False, default=False,
                    help="Do you want to HA this environment?")

parser.add_argument('--dir_service', action='store', dest='dir_service', required=False, default=False,
                    help="Will this cluster use a form of directory management?")

parser.add_argument('--dir_version', action='store', dest='dir_version', required=False, default='openldap',
                    help="Which form of directory management will it use? (openldap/389)")

parser.add_argument('--os', action="store", dest="os", required=False, default='ubuntu', 
                    help="Operating System to use for Open Stack")

parser.add_argument('--action', action="store", dest="action", required=False, default="build", 
                    help="Action to do for Open Stack (build/destroy/add)")

#Defaulted arguments
parser.add_argument('--razor_ip', action="store", dest="razor_ip", default="198.101.133.3",
                    help="IP for the Razor server")
parser.add_argument('--chef_url', action="store", dest="chef_url", default="https://198.101.133.3:443", required=False, 
                    help="URL of the chef server")
parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, 
                    help="client for chef")
parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="~/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

parser.add_argument('--clear_pool', action="store", dest="clear_pool", default=True, required=False)

# Save the parsed arguments
results = parser.parse_args()
results.chef_client_pem = results.chef_client_pem.replace('~',os.getenv("HOME"))

# Convert parameter string to boolean
ha_enabled = False
if results.ha_enabled == 'true':
    ha_enabled = True

dir_service = False
if results.dir_service == 'true':
    dir_service = True

def build_computes(computes):
    # Run computes
    print "Making the compute nodes..."
    for compute in computes:
        compute_node = Node(compute)
        compute_node['in_use'] = "compute"
        compute_node.run_list = ["role[qa-single-compute]"]
        compute_node.save()

        print "Updating server...this may take some time"
        update_node(compute_node)

        if compute_node['platform_family'] == 'rhel':
            print "Platform is RHEL family, disabling iptables"
            disable_iptables(compute_node)

        # Run chef client twice
        print "Running chef-client on compute node: %s, this may take some time..." % compute
        run1 = run_chef_client(compute_node)
        if run1['success']:
            print "First chef-client run successful...starting second run..."
            run2 = run_chef_client(compute_node)
            if run2['success']:
                print "Second chef-client run successful..."
            else:
                print "Error running chef-client for compute %s" % compute
                print run2
                sys.exit(1)
        else:
            print "Error running chef-client for compute %s" % compute
            print run1
            sys.exit(1)

def build_controller(controller, ha=False, ha_num=0):
    controller_node = Node(controller)

    # Check for ha
    if ha:
        print "Making %s the ha-controller%s node" % (controller, ha_num)
        controller_node['in_use'] = "ha-controller%s" % ha_num
        controller_node.run_list = ["role[qa-ha-controller%s]" % ha_num]
    else:
        print "Making %s the controller node" % controller
        controller_node['in_use'] = "controller"
        controller_node.run_list = ["role[qa-single-controller]"]
    # save node
    controller_node.save()

    print "Updating server...this may take some time"
    update_node(controller_node)

    if controller_node['platform_family'] == 'rhel':
        print "Platform is RHEL family, disabling iptables"
        disable_iptables(controller_node)

    # Run chef-client twice
    print "Running chef-client for controller node...this may take some time..."
    run1 = run_chef_client(controller_node)
    if run1['success']:
        print "First chef-client run successful...starting second run..."
        run2 = run_chef_client(controller_node)
        if run2['success']:
            print "Second chef-client run successful..."
        else:
            print "Error running chef-client for controller %s" % controller
            print run2
            sys.exit(1)
    else:
        print "Error running chef-client for controller %s" % controller
        print run1
        sys.exit(1)

def build_dir_server(dir_server):
    # We dont support 389 yet, so exit if it is not ldap
    if results.dir_version != 'openldap':
        print "%s as a directory service is not yet supported...exiting" % results.dir_version
        sys.exit(1)

    # Build directory service node
    dir_node = Node(dir_server)
    ip = dir_node['ipaddress']
    root_pass = razor.get_active_model_pass(dir_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    dir_node['in_use'] = 'directory-server'
    dir_node.run_list = ["role[qa-%s-%s]" % (results.dir_version, results.os)]
    dir_node.save()

    print "Updating server...this may take some time"
    update_node(dir_node)

    # if redhat platform, disable iptables
    if dir_node['platform_family'] == 'rhel':
        print "Platform is RHEL family, disabling iptables"
        disable_iptables(dir_node)

    # Run chef-client twice
    print "Running chef-client for directory service node...this may take some time..."
    run1 = run_chef_client(dir_node)
    if run1['success']:
        print "First chef-client run successful...starting second run..."
        run2 = run_chef_client(dir_node)
        if run2['success']:
            print "Second chef-client run successful..."
        else:
            print "Error running chef-client for directory node %s" % dir_node
            print run2
            sys.exit(1)
    else:
        print "Error running chef-client for directory node %s" % dir_node
        print run1
        sys.exit(1)

    # Directory service is set up, need to import config
    if run1['success'] and run2['success']:
        if results.dir_version == 'openldap':
            scp_run = run_remote_scp_cmd(ip, 'root', root_pass, '/var/lib/jenkins/source_files/ldif/*.ldif')
            if scp_run['success']:
                ssh_run = run_remote_ssh_cmd(ip, 'root', root_pass, 'ldapadd -x -D \"cn=admin,dc=dev,dc=rcbops,dc=me\" -f base.ldif -w@privatecloud')
        elif results.dir_version == '389':
            # Once we support 389, code here to import needed config files
            print "389 is not yet supported..."
            sys.exit(1)
        else:
            print "%s is not supported...exiting" % results.dir_version
            sys.exit(1)

    if scp_run['success'] and ssh_run['success']:
        print "Directory Service: %s successfully set up..." % results.dir_version
    else:
        print "Failed to set-up Directory Service: %s..." % results.dir_version
        sys.exit(1)

def check_cluster_size(chef_nodes, size):
    if len(chef_nodes) < size:
        print "*****************************************************"
        print "Not enough nodes for the cluster_size given: %s " % cluster_size
        print "*****************************************************"
        sys.exit(1)

def clear_pool(chef_nodes, environment):
    for n in chef_nodes:
        name = n['name']
        node = Node(name)
        if node.chef_environment == environment:
            if "recipe[network-interfaces]" not in node.run_list:
                erase_node(name)
            else:
                node.chef_environment = "_default"
                node.save()

def disable_iptables(chef_node, logfile="STDOUT"):
    ip = chef_node['ipaddress']
    root_pass = razor.get_active_model_pass(chef_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    return run_remote_ssh_cmd(ip, 'root', root_pass, '/etc/init.d/iptables save; /etc/init.d/iptables stop; /etc/init.d/iptables save')

def erase_node(name):
    print "Deleting: %s" % (name)
    node = Node(name)  
    am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
    run = run_remote_ssh_cmd(node['ipaddress'], 'root', razor.get_active_model_pass(am_uuid)['password'], "reboot 0")
    if not run['success']:
        print "Error rebooting server %s " % node['ipaddress']
        sys.exit(1)        
    
    # Remove node and client from chef server
    Client(name).delete()
    Node(name).delete()                
    
    #Remove active model          
    razor.remove_active_model(am_uuid)                            
    time.sleep(15)

def environment_has_controller(environment):
    # Load Environment
    nodes = Search('node').query("chef_environment:%s" % environment)
    roles = ['role[qa-single-controller', 'role[qa-ha-controller1]', 'role[qa-ha-controller2]']
    for node in nodes:
        chef_node = Node(node['name'])
        if any(x in chef_node.run_list for x in roles):
            return True
        else:
            return False

def gather_nodes(chef_nodes, environment, cluster_size):
    ret_nodes = []
    count = 0

    # Take a node from the default environment that has its network interfaces set.
    for n in chef_nodes:
        name = n['name']
        node = Node(name)
        if ((node.chef_environment == "_default" or node.chef_environment == environment) and "recipe[network-interfaces]" in node.run_list):
            node['in_use'] = 1
            set_nodes_environment(node, environment)
            ret_nodes.append(name)          
            print "Taking node: %s" % name
            count += 1

            if count >= cluster_size:
                break

    if count < cluster_size:
        print "Not enough available nodes for requested cluster size of %s, try again later..." % cluster_size
        sys.exit(1)

    return ret_nodes

def print_server_info(name):
    node = Node(name)
    return "%s - %s" % (name, node['ipaddress'])

def print_computes_info(computes):
    for compute in computes:
        print "Compute: %s" % print_server_info(compute)

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

def run_chef_client(chef_node, logfile="STDOUT"):
    ip = chef_node['ipaddress']
    root_pass = razor.get_active_model_pass(chef_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    return run_remote_ssh_cmd(ip, 'root', root_pass, 'chef-client --logfile %s' % logfile)

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

def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
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

def set_network_interfaces(chef_nodes):
    for n in chef_nodes:
        node = Node(n['name'])
        if "role[qa-base]" in node.run_list:
            node.run_list = ["recipe[network-interfaces]"]
            node.save()
            print "Running network interfaces for %s" % node.name
          
            #Run chef client thrice
            run1 = run_chef_client(node, logfile="/dev/null")
            run2 = run_chef_client(node, logfile="/dev/null")
            run3 = run_chef_client(node, logfile="/dev/null")

            if run1['success'] and run2['success'] and run3['success']:
                print "Done running chef-client"
            else:
                print "Error running chef client for network interfaces"
                print "First run: %s" % run1
                print "Second run: %s" % run2
                print "Final run: %s" % run3
                sys.exit(1)

def set_nodes_environment(chef_node, environment):
    if chef_node.chef_environment != environment:
        chef_node.chef_environment = environment
        chef_node.save()

def update_node(chef_node):
    ip = chef_node['ipaddress']
    root_pass = razor.get_active_model_pass(node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    if node['platform_family'] == "debian":
        run_remote_ssh_cmd(ip, 'root', root_pass, 'apt-get update -y -qq')
    elif node['platform_family'] == "rhel":
        run_remote_ssh_cmd(ip, 'root', root_pass, 'yum update -y -q')
    else:
        print "Platform Family %s is not supported." % node['platform_family']
        sys.exit(1)

"""
Steps
1. Make an environment for {{name}}-{{os}}-openstack
2. Grab (cluster_size) amount of active models and change their env to {{os}}-{{name}}
3. Pick one for the controller, set roles, run chef-client
4. Pick the rest as computes, set roles, run chef-client
"""

with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)

    # Remove broker fails for qa-%os-pool
    remove_broker_fail("qa-%s-pool" % results.os)

    #Prepare environment
    nodes = Search('node').query("name:qa-%s-pool*" % results.os)

    #Make sure all networking interfacing is set
    set_network_interfaces(nodes)

    # If the environment doesnt exist in chef, make it.
    env = "%s-%s" % (results.os, results.name)
    if not Search("environment").query("name:%s"%env):
        print "Making environment: %s " % env
        Environment.create(env)

    # Set the cluster size   
    cluster_size = int(results.cluster_size)

    # Collect environment and install Open Stack.
    if results.action == "build":

        # If we want to clear the pool
        if results.clear_pool:
            clear_pool(nodes, env)

        # Check the cluster size, if <5 and dir_service is enabled, set to 4
        if cluster_size < 4 and dir_service:
            if ha_enabled:
                cluster_size = 5
                print "HA and Directory Services are requested, re-setting cluster size to %i." % cluster_size
            else:
                cluster_size = 4
                print "Directory Services are requested, re-setting cluster size to %i." % cluster_size
        elif cluster_size < 4 and ha_enabled:
            cluster_size = 4
            print "HA is enabled, re-setting cluster size to %i." % cluster_size
        else:
            print "Cluster size is %i." % cluster_size

        #Collect the amount of servers we need for the openstack install
        check_cluster_size(nodes, cluster_size)        

        # gather the nodes and set there environment
        openstack_list = gather_nodes(nodes, env, cluster_size)

        # If there were no nodes available, exit
        if not openstack_list:
            print "No nodes available..."
            sys.exit(1)

        # Build cluster accordingly
        if dir_service and ha_enabled:
            
            # Set each servers roles
            dir_service = openstack_list[0]
            ha_controller_1 = openstack_list[1]
            ha_controller_2 = openstack_list[2]
            computes = openstack_list[3:]

            # Build directory service server
            build_dir_server(dir_service)

            # Build HA Controllers
            build_controller(ha_controller_1, True, 1)
            build_controller(ha_controller_2, True, 2)

            # Have to run chef client on controller 1 again
            ha_controller_1_node = Node(ha_controller_1)
            run_chef_client(ha_controller_1_node)

            # Build computes
            build_computes(computes)

            # print all servers info
            print "********************************************************************"
            print "Directory Service Server: %s" % print_server_info(dir_service)
            print "HA-Controller 1: %s" % print_server_info(ha_controller_1)
            print "HA-Controller 2: %s" % print_server_info(ha_controller_2)
            print_computes_info(computes)
            print "********************************************************************"

        elif dir_service:
            
            # Set each servers roles
            dir_service = openstack_list[0]
            controller = openstack_list[1]
            computes = openstack_list[2:]

            # Build the dir server
            build_dir_server(dir_service)

            # Build controller
            build_controller(controller)

            # Build computes
            build_computes(computes)

            # print all servers info
            print "********************************************************************"
            print "Directory Service Server: %s" % print_server_info(dir_service)
            print "Controller: %s" % print_server_info(controller)
            print_computes_info(computes)
            print "********************************************************************"

        elif ha_enabled:
            
            # Set each servers roles
            ha_controller_1 = openstack_list[0]
            ha_controller_2 = openstack_list[1]
            computes = openstack_list[2:]

            # Make the controllers
            build_controller(ha_controller_1, True, 1)
            build_controller(ha_controller_2, True, 2)

            # Have to run chef client on controller 1 again
            ha_controller_1_node = Node(ha_controller_1)
            print "HA Setup...have to run chef client on %s again cause it is ha-controller1..." % ha_controller_1
            run_chef_client(ha_controller_1_node)

            # build computes
            build_computes(computes)

            # print all servers info
            print "********************************************************************"
            print "HA-Controller 1: %s" % print_server_info(ha_controller_1)
            print "HA-Controller 2: %s" % print_server_info(ha_controller_2)
            print_computes_info(computes)
            print "********************************************************************"
        else:
            
            # Set each servers roles
            controller = openstack_list[0]
            computes = openstack_list[1:]

            # Make servers
            build_controller(controller)
            build_computes(computes)

            # print all servers info
            print "********************************************************************"
            print "Controller: %s" % print_server_info(controller)
            print_computes_info(computes)
            print "********************************************************************"

    # We want to add more nodes to the environment
    elif results.action == 'add':

        # make sure there is a controller
        if environment_has_controller(env):

            # make sure we have enough nodes
            check_cluster_size(nodes, cluster_size)

            # set all nodes to compute in the requested environment
            computes = gather_nodes(nodes, env, cluster_size)

            # If there were no nodes available, exit
            if not computes:
                print "No nodes available..."
                sys.exit(1)

            # Build out the computes
            build_computes(computes)
            print_computes_info(computes)

        else:
            print "Chef Environment %s doesnt have a controller, cant take action %s" % (env, results.action)
            sys.exit(1)

    elif results.action == 'destroy':
        clear_pool(nodes, env)

    else:
        print "Action %s is not supported..." % results.action
        sys.exit(1)