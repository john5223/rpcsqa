#!/usr/bin/python

import os
import subprocess
import json
import argparse
import cloudaccount
import cloudservers

"""
	Builds servers for an account in RS Public Cloud and saves Account Info in current directory
"""

# Gather the argumetn from the command line
parser = argparse.ArgumentParser()

# Get the username for the Rackspace Public Cloud Account
parser.add_argument('--username', action="store", dest="username", 
					help="User name for the account")

# Get the apikey for the Rackspace Public Cloud Account
parser.add_argument('--apikey', action="store", dest="apikey", 
					help="api key for the account")

# Get the number of servers to create
parser.add_argument('--number', action="store", dest="num_servers", 
					help="Number of servers to create.")

# Get the name of the server
parser.add_argument('--name', action="store", dest="server_name", 
					help="Name of server.")

# Get the name of the project to put the server in
parser.add_argument('--project', action="store", dest="project_name", 
					help="Name of project that servers will belong to.")

# Get the OS image to use on the server
parser.add_argument('--os', action="store", dest="os_image", 
					help="Operating system to install.")

# Get the flavor that the server will use
parser.add_argument('--flavor', action="store", dest="server_flavor", 
					help="Flavor of Server to use ( in MB, GB, etc.).")

# Get the datacenter to create the servers in ( ex. DFW, ORD)
parser.add_argument('--dc', action="store", dest="dc", 
					help="Datacenter to place the servers in(dfw|ord). ")

# Save the parameters
results = parser.parse_args()

# Create the account info
account_info = cloudaccount.generate_account_info(results.username, results.apikey)

# Create a dict of the URLS for the API for the account
urls = cloudaccount.urls(account_info['catalogs'])

# Create a dict of the flavors for the account
flavors = cloudaccount.flavors(urls[results.dc], account_info['authtoken'])

# Create a dict of the images for the account
images = cloudaccount.images(urls[results.dc], account_info['authtoken'])

# build the list of personalities to use, this will become parameters (maybe)
#personalities = cloudservers.add_personalities([{'path': '/opt/rpcs/rpcs.conf', 'filename': 'rpcs.conf'},
#											   {'path': '/opt/rpcs/post-install.sh', 'filename': 'post-install.sh'},
#											   {'path': '/opt/rpcs/functions.sh', 'filename': 'functions.sh'}])

#print json.dumps(personalities, indent=2)

# Build the servers
new_servers = cloudservers.build_servers(account_info['authtoken'], 
									   urls['dfw'], 
									   results.server_name, 
									   results.num_servers,
									   images[results.os_image], 
									   results.os_image, 
									   results.project_name, 
									   flavors[results.server_flavor],
									   None
									   )

# Print the created servers (DEBUG)
for server in new_servers:
	print json.dumps(server, indent=2)

build_info = {'account_num' : account_info['account'],
			  'authtoken' : account_info['authtoken'],
			  'urls' : urls,
			  'new_servers' : new_servers,
			  'server_name' : results.server_name
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
	print "!! %s.json file write successful to directory %s" % (results.username, subprocess.call('pwd'))
# End Script