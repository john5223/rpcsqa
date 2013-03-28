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
                    help="Action to do for Open Stack (build/destroy)")

#Defaulted arguments
parser.add_argument('--razor_ip', action="store", dest="razor_ip", default="198.101.133.3",
                    help="IP for the Razor server")
parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.3:4000", required=False, 
                    help="URL of the chef server")
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
               
def run_chef_client(chef_node, logfile="STDOUT"):
    ip = chef_node['ipaddress']
    root_pass = razor.get_active_model_pass(chef_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    return run_remote_ssh_cmd(ip, 'root', root_pass, 'chef-client --logfile %s' % logfile)

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

def make_dir_server(dir_server):
    with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
        dir_node = Node(dir_server)
        dir_node['in_use'] = 'directory-server'
        dir_node.run_list = "role[qa-%s-%s]" % (results.dir_version, results.os)
        dir_node.save()

        # Run chef-client twice
        print "Running chef-client for directory service node...this may take some time..."
        run1 = run_chef_client(dir_node)
        if run1['success']:
            print "First chef-client run successful...starting second run..."
            run2 = run_chef_client(dir_node)
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

def make_controller(controller, ha=False, ha_num=0):
    with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
        controller_node = Node(controller)

        # Check for ha
        if ha:
            print "Making %s the ha-controller%s node" % controller
            controller_node['in_use'] = "ha-controller%s" % ha_num
            controller_node.run_list = "role[qa-ha-controller%s]" % ha_num
        else:
            print "Making %s the controller node" % controller
            controller_node['in_use'] = "controller"
            controller_node.run_list = "role[qa-single-controller]"
        # save node
        controller_node.save()

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

def make_computes(computes):
    with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
        # Run computes
        print "Making the compute nodes..."
        for compute in computes:
            compute_node = Node(compute)
            compute_node['in_use'] = "compute"
            compute_node.run_list = "role[qa-single-compute]"
            compute_node.save()

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
"""
Steps
1. Make an environment for {{name}}-{{os}}-openstack
2. Grab (cluster_size) amount of active models and change their env to {{os}}-{{name}}
3. Pick one for the controller, set roles, run chef-client
4. Pick the rest as computes, set roles, run chef-client
"""

with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    razor = razor_api(results.razor_ip)

    # Remove broker fails from qa-ubuntu-pool.
    remove_broker_fail("qa-ubuntu-pool")
    time.sleep(3)
    remove_broker_fail("qa-centos-pool")

    # If the environment doesnt exist in chef, make it.
    env = "%s-%s" % (results.os, results.name)
    if not Search("environment").query("name:%s"%env):
        print "Making environment: %s " % env
        Environment.create(env)

    # Set the cluster size   
    cluster_size = int(results.cluster_size)

    # Check the cluster size, if <5 and dir_service is enabled, set to 4
    if cluster_size < 4 and results.dir_service:
        if results.ha_enabled:
            print "HA and Directory Services are requested, setting cluster size to 5"
            cluster_size = 5
        else:
            print "Directory Services are requested, setting cluster size to 4"
            cluster_size = 4
    elif cluster_size < 4 and results.ha_enabled:
        print "HA is enabled, setting cluster size to 4"
        cluster_size = 4

    #Prepare environment
    nodes = Search('node').query("name:qa-%s-pool*" % results.os)

    #Make sure all networking interfacing is set
    for n in nodes:
        node = Node(n['name'])
        if "recipe[network-interfaces]" not in node.run_list:
            node.run_list = "recipe[network-interfaces]"
            node.save()
            print "Running network interfaces for %s" % node.name
          
            #Run chef client thrice
            run1 = run_chef_client(node.name, logfile="/dev/null")
            run2 = run_chef_client(node.name, logfile="/dev/null")
            run3 = run_chef_client(node.name, logfile="/dev/null")

            if run1['success'] and run2['success'] and run3['success']:
                print "Done running chef-client"
            else:
                print "Error running chef client for network interfaces"
                print "First run: %s" % run1
                print "Second run: %s" % run2
                print "Final run: %s" % run3
                sys.exit(1)

    # If we want to clear the pool
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

    # Collect environment and install Open Stack.
    if results.action == "build":          
        #Collect the amount of servers we need for the openstack install
        nodes = Search('node').query("name:qa-%s-pool*" % results.os)
        if len(nodes) < cluster_size:
            print "*****************************************************"
            print "Not enough nodes for the cluster_size given: %s " % cluster_size
            print "*****************************************************"
            sys.exit(1)          
        
        count = 0
        openstack_list = []
        
        for n in nodes:
            name = n['name']
            node = Node(name)
            if node.chef_environment == "_default" and "recipe[network-interfaces]" in node.run_list:
                node['in_use'] = 1
                node.chef_environment = env
                node.save()
                openstack_list.append(name)          
                print "Taking node: %s" % name
                count += 1
                if count >= cluster_size:
                    break

        if not openstack_list:
            print "No nodes"
            sys.exit(1)

        # Build cluster accordingly
        if results.dir_service and results.ha_enabled:
            # Set each servers roles
            dir_service = openstack_list[0]
            ha_controller_1 = openstack_list[1]
            ha_controller_2 = openstack_list[2]
            computes = openstack_list[3:]

            # make each server
            make_dir_server(dir_service)
            make_controller(ha_controller_1, True, 1)
            make_controller(ha_controller_2, True, 2)
            run_chef_client(ha_controller_1)
            make_computes(computes)

        elif results.dir_service:
            # Set each servers roles
            dir_service = openstack_list[0]
            controller = openstack_list[1]
            computes = openstack_list[2:]

            #make the servers
            make_dir_server(dir_service)
            make_controller(controller)
            make_computes(computes)

        elif results.ha_enabled:
            # Set each servers roles
            ha_controller_1 = openstack_list[0]
            ha_controller_2 = openstack_list[1]
            computes = openstack_list[2:]

            # Make the servers
            make_controller(ha_controller_1, True, 1)
            make_controller(ha_controller_2, True, 2)
            make_computes(computes)
        else:
            # Set each servers roles
            controller = openstack_list[0]
            computes = openstack_list[1:]

            # Make servers
            make_controller(controller)
            make_computes(computes)
