#!/usr/bin/python

import os
import json
import subprocess
import cloudservers
import cloudaccount
import argparse

"""
	This script will teardown the Cloud Servers environment that we set up via previous scripts
"""

#Start the script
print "!!## -- Begin Tearing Down Virtualized Infrastructure -- ##!!"

# Gather the argumetn from the command line
parser = argparse.ArgumentParser()

# Get the username for the Rackspace Public Cloud Account
parser.add_argument('--username', action="store", dest="username", 
					help="User name for the account")

# Get the apikey for the Rackspace Public Cloud Account
parser.add_argument('--apikey', action="store", dest="apikey", 
					help="api key for the account")

# Get the name of the server
parser.add_argument('--server_name', action="store", dest="server_name", 
					help="Name of server.")

# Get the datacenter to create the servers in ( ex. DFW, ORD)
parser.add_argument('--dc', action="store", dest="dc", 
					help="Datacenter to place the servers in(dfw|ord). ")

# Save the parameters
results = parser.parse_args()

# Change to the workspace directory, if it doesnt exist, catch the error
workspace_dir = '/var/lib/jenkins/workspace'
try:
	os.chdir(workspace_dir)
	# Run git command to print current commit hash
	subprocess.call(['git', 'log', '-1'])
except OSError:
	print "No Such Directory : %s" % (workspace_dir)

# Run Things
print "!!## -- Start Tearing Down Virtualized Infrastructure -- ##!!"

# gather account info
account_info = cloudaccount.generate_account_info(results.username, results.apikey)

# Create a dict of the URLS for the API for the account
urls = cloudaccount.urls(account_info['catalogs'])

## Gather the current servers
servers = cloudaccount.servers(urls[results.dc], account_info['authtoken'])

to_delete_servers = []
for server in servers:
	if results.server_name in server:
		to_delete_servers.append(servers[server]['id'])

# Run delete servers
deleted_servers = cloudservers.delete_servers(account_info['authtoken'], urls[results.dc], to_delete_servers)

# Print the result of delete_servers
print "The results of delete servers : "
print deleted_servers

print "!!## -- Finished Tearing Down Virtualized Infrastructure -- ##!!"