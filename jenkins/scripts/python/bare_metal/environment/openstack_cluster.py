#!/usr/bin/python
import os
import sys
import time
import requests
import argparse
from rpcsqa_helper import *
from chef import Search, Environment, Node

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()
parser.add_argument('--name', action="store", dest="name", required=False, default="glance-cf", 
                    help="This will be the name for the Open Stack chef environment")

parser.add_argument('--cluster_size', action="store", dest="cluster_size", required=False, default=4, 
                    help="Size of the Open Stack cluster.")

parser.add_argument('--ha_enabled', action='store_true', dest='ha_enabled', required=False, default=False,
                    help="Do you want to HA this environment?")

parser.add_argument('--dir_service', action='store_true', dest='dir_service', required=False, default=False,
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

parser.add_argument('--clear_pool', action="store_true", dest="clear_pool", default=True, required=False)

# Save the parsed arguments
results = parser.parse_args()
results.chef_client_pem = results.chef_client_pem.replace('~',os.getenv("HOME"))

"""
Steps
1. Make an environment for {{name}}-{{os}}-openstack
2. Grab (cluster_size) amount of active models and change their env to {{os}}-{{name}}
3. Pick one for the controller, set roles, run chef-client
4. Pick the rest as computes, set roles, run chef-client
"""
rpcsqa = rpcsqa_helper(results.razor_ip)
chef = rpcsqa.chef
razor = rpcsqa.razor

with chef:

    # Remove broker fails for qa-%os-pool
    remove_broker_fail("qa-%s-pool" % results.os)

    #Prepare environment
    nodes = Search('node').query("name:qa-%s-pool*" % results.os)

    #Make sure all networking interfacing is set
    for node in nodes:
        chef_node = Node(node['name'])
        set_network_interface(chef_node)

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

        # Check the cluster size, if <5 and results.dir_service is enabled, set to 4
        if cluster_size < 4 and results.dir_service:
            if results.ha_enabled:
                cluster_size = 5
                print "HA and Directory Services are requested, re-setting cluster size to %i." % cluster_size
            else:
                cluster_size = 4
                print "Directory Services are requested, re-setting cluster size to %i." % cluster_size
        elif cluster_size < 4 and results.ha_enabled:
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
        if results.dir_service and results.ha_enabled:
            
            # Set each servers roles
            dir_server = openstack_list[0]
            ha_controller_1 = openstack_list[1]
            ha_controller_2 = openstack_list[2]
            computes = openstack_list[3:]

            # Build directory service server
            build_dir_server(dir_server)

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
            print "Directory Service Server: %s" % print_server_info(dir_server)
            print "HA-Controller 1: %s" % print_server_info(ha_controller_1)
            print "HA-Controller 2: %s" % print_server_info(ha_controller_2)
            print_computes_info(computes)
            print "********************************************************************"

        elif results.dir_service:
            
            # Set each servers roles
            dir_server = openstack_list[0]
            controller = openstack_list[1]
            computes = openstack_list[2:]

            # Build the dir server
            build_dir_server(dir_server)

            # Build controller
            build_controller(controller)

            # Build computes
            build_computes(computes)

            # print all servers info
            print "********************************************************************"
            print "Directory Service Server: %s" % print_server_info(dir_server)
            print "Controller: %s" % print_server_info(controller)
            print_computes_info(computes)
            print "********************************************************************"

        elif results.ha_enabled:
            
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