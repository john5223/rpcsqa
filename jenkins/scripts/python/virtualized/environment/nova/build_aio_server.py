#!/usr/bin/python

import os
import subprocess
import json
import argparse
import novaaccount
import novaservers

""" Builds an AIO Server on the given Nova Account """

# Gather the arguments from the command line
parser = argparse.ArgumentParser()

# Get the role for the server
parser.add_argument('--url', action="store", dest="url", 
					help="URL of the Alamo AIO Cluster")

# Get the interface for the public network
parser.add_argument('--username', action="store", dest="username", 
					help="Username of the user building the server")

# Get the interface for the private network
parser.add_argument('--password', action="store", dest="password", 
					help="Password of the user building the server")

# Get the IP address of the controller
parser.add_argument('--tenant_id', action="store", dest="tenant_id", 
					help="Tenant name of the user building the server")

# Get the number of servers to create
parser.add_argument('--num_servers', action="store", dest="num_servers", 
					help="Number of servers to create.")

# Get the name of the server
parser.add_argument('--server_name', action="store", dest="server_name", 
					help="Name of server.")

# Get the OS image to use on the server
parser.add_argument('--os_image', action="store", dest="os_image", 
					help="Operating system to install.")

# Get the flavor that the server will use
parser.add_argument('--server_flavor', action="store", dest="server_flavor", 
					help="Flavor of Server to use ( in MB, GB, etc.).")

# Get the flavor that the server will use
parser.add_argument('--key_name', action="store", dest="key_name", 
					help="Key to generate server with")

# Parse the parameters
results = parser.parse_args()

# Debug printing
#print results

# Change to the workspace directory, if it doesnt exist, catch the error
workspace_dir = '/var/lib/jenkins/workspace'
try:
	os.chdir(workspace_dir)
	# Run git command to print current commit hash
	subprocess.call(['git', 'log', '-1'])
except OSError:
	print "No Such Directory : %s" % (workspace_dir)

## Build a Ubuntu 12.04 Server on our All-In-One box
# Authenticate against our Alamo Install

# Gather Auth info
account_info = novaaccount.generate_account_info(results.url, results.username, results.password, results.tenant_id)

# Print debugging
print "Authtoken : " + account_info['authtoken']
print "Account / Tenant : " + account_info['account']
#print json.dumps(account_info, indent=2)

# Gather URL endpoints
urls = novaaccount.urls(account_info['catalogs'])

# Print debugging
#print json.dumps(urls, indent=2)

# Gather available images
images = novaaccount.images(urls['nova'], account_info['authtoken'])

# Print debugging
print json.dumps(images, indent=2)

# Gather available flavors
flavors = novaaccount.flavors(urls['nova'], account_info['authtoken'])

# Print debugging
print json.dumps(flavors, indent=2)

# Gather running servers
servers = novaaccount.servers(urls['nova'], account_info['authtoken'])

# Print debugging
print json.dumps(servers, indent=2)

# build the list of personalities to use, this will become parameters (maybe)
post_install = {'path': '/opt/rpcs/post-install.sh', 'filename': 'post-install.sh'}
personalities = novaservers.add_personalities([])

print json.dumps(personalities, indent=2)

# Build the server(s)
new_servers = novaservers.build_servers(account_info['authtoken'],
										urls['nova'],
										results.server_name,
										results.num_servers,
										images[results.os_image],
										results.os_image,
										results.tenant_id,
										flavors[results.server_flavor],
										personalities,
										results.key_name)

# print debugging
print "Created Servers : "
print json.dumps(new_servers, indent=2)

build_info = {'account_num' : account_info['account'],
			  'authtoken' : account_info['authtoken'],
			  'urls' : urls,
			  'new_servers' : new_servers,
			  'server_name' : results.server_name,
			  'key-name' : results.key_name
			  }

# Write build_info as a json file
try:
	# Open the file
	fo = open("%s-build.json" % (results.username), "w")
except IOError:
	print "Failed to open file %s-build.json" % (results.username)
else:
	# Write the json string
	fo.write(json.dumps(build_info, indent=2))
	
	#close the file
	fo.close()
	
	# print out successfull write text
	print "!! %s-build.json file write successful to directory %s" % (results.username, subprocess.call('pwd'))

print "!!## -- End Build AIO Nova Environment -- ##!!"