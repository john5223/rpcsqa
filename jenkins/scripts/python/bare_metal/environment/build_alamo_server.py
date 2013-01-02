#!/usr/bin/python

import os
import subprocess
import json
import argparse
from ssh_session import ssh_session

""" 
	This script will run from Jenkins and call Razor to build a server at the given IP.
    It will also build the rpcs.cfg file.
    Author: Solomon Wagner
"""

# Gather the argument from the command line
parser = argparse.ArgumentParser()

# Get the role for the server
parser.add_argument('--server_ip', action="store", dest="server_ip", 
					type=str, required=True, help="IP of the server")

# Get the role for the server
parser.add_argument('--role', action="store", dest="role", 
					type=str, default="All-In-One", help="Role for the server (Controller / All-In-One / Compute")

# Get the interface for the public network
parser.add_argument('--net_public_iface', action="store", dest="net_public_iface", 
					type=str, default="eth0", help="Interface for the public network")

# Get the interface for the private network
parser.add_argument('--net_private_iface', action="store", dest="net_private_iface", 
					type=str, default="eth1", help="Interface for the private network")

# Get the IP address of the controller
parser.add_argument('--net_con_ip', action="store", dest="net_con_ip", 
					type=str, default="", help="IP address of the controller")

# Get the CIDR block for the Nova Management Network
parser.add_argument('--net_mgmt', action="store", dest="net_mgmt",
					type=str, default="", help="CIDR block for the Nova Management Network")

# Get the CIDR block for the nova network
parser.add_argument('--net_nova', action="store", dest="net_nova", 
					type=str, default="", help="CIDR block for the nova network")

# Get the CIDR block for the public network
parser.add_argument('--net_public', action="store", dest="net_public", 
					type=str, default="", help="CIDR block for the public network")

# Get the CIDR block for the Nova Fixed (VM) Network
parser.add_argument('--net_fixed', action="store", dest="net_fixed", 
					type=str, default="172.31.0.0/24", help="CIDR block for the Nova Fixed (VM) Network")

# Get the CIDR block for the DMZ Network
parser.add_argument('--net_dmz', action="store", dest="net_dmz", 
					type=str, default="", help="CIDR block for the DMZ Network")

# Get the gateway for the DMZ
parser.add_argument('--net_dmz_gateway', action="store", dest="net_dmz_gateway", 
					type=str, default="", help="Gateway for the DMZ network")

# Get the name of the Nova Fixed Bridge Interface
parser.add_argument('--net_bridge', action="store", dest="net_bridge", 
					type=str, default="br0", help="Name of the Nova Fixed Bridge Interface")

# Get the password for the openstack admin user
parser.add_argument('--os_admin_user', action="store", dest="os_admin_user", 
					type=str, default="administrator", help="Username for the OpenStack admin user")

# Get the password for the openstack admin user
parser.add_argument('--os_admin_passwd', action="store", dest="os_admin_passwd", 
					type=str, default="admin", help="Password for the OpenStack admin user")

# Get the username for a normal Openstack user
parser.add_argument('--os_user_name', action="store", dest="os_user_name", 
					type=str, default="demo", help="Username for the normal OpenStack user")

# Get the password for the normal Openstack user
parser.add_argument('--os_user_passwd', action="store", dest="os_user_passwd", 
					type=str, default="demo", help="Password for the normal OpenStack user")

# Save the parameters
results = parser.parse_args()

# Convert the passed parameters to a json for easy consumption and file writing
server_config = {
	'role' : results.role,
	'net_public_iface' : results.net_public_iface,
	'net_private_iface' : results.net_private_iface,
	'net_con_ip' : results.net_con_ip,
	'net_mgmt' : results.net_mgmt,
	'net_nova' : results.net_nova,
	'net_public' : results.net_public,
	'net_fixed' : results.net_fixed,
	'net_dmz' : results.net_dmz,
	'net_dmz_gateway' : results.net_dmz_gateway,
	'net_bridge' : results.net_bridge,
	'os_admin_passwd' : results.os_admin_passwd,
	'os_user_name' : results.os_user_name,
	'os_user_passwd' : results.os_user_passwd,
	'precise_url' : 'file:///opt/rpcs/precise-server-cloudimg-amd64.tar.gz',
	'cirros_url': 'file:///opt/rpcs/cirros-0.3.0-x86_64-uec.tar.gz'
}

# This is where we would call the Razor API to build the server
# !! This is not being done atm, once we have razor set up we will code it here !!

# Check the networking information, if things are missing, go get them
for item in server_config:
	if server_config[item] == "None":
		print "%s : %s : %s" % (item, type(server_config[item]), 'empty')
		server_config[item] = ''

# Write the rpcs.cfg file
print "Write %s-rpcs.cfg..." % results.server_ip
try:
	# Open the file
	fo = open("%s-rpcs.cfg" % (results.server_ip),"w")
except IOError:
	print "...Failed to open file rpcs.cfg. Exiting..."
	print "...%s-rpcs.cfg failed to write successfully."
else:
	# Write cfg file
	for item in server_config:
		to_write_string = '%s="%s"\n' % (item, server_config[item])
		fo.write(to_write_string)

	fo.close()
	print "...%s-rpcs.cfg written successfully!!" % (results.server_ip)

print "!!## -- Build Alamo Server Finished -- ##!!"