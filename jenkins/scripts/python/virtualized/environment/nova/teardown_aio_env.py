#!/usr/bin/python

import os
import json
import subprocess
import novaservers
import novaaccount
import argparse

"""This script will teardown the Cloud Servers environment that we set up via previous scripts"""

#Start the script
print "!!## -- Begin Tearing Down Virtualized Infrastructure -- ##!!"

# Gather the argumetn from the command line
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

# Get the name of the server
parser.add_argument('--server_name', action="store", dest="server_name", 
					help="Name of server.")

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

# Gather Auth info
account_info = novaaccount.generate_account_info(results.url, results.username, results.password, results.tenant_id)

# Print debugging
print "Authtoken : " + account_info['authtoken']
print "Account / Tenant : " + account_info['account']
#print json.dumps(account_info, indent=2)

# Gather URL endpoints
urls = novaaccount.urls(account_info['catalogs'])

# Print debugging
print json.dumps(urls, indent=2)

# Gather running servers
servers = novaaccount.servers(urls['nova'], account_info['authtoken'])

# Print debugging
print json.dumps(servers, indent=2)

to_delete_servers = []
for server in servers:
	if results.server_name in server:
		to_delete_servers.append(servers[server]['id'])

# Run delete servers
deleted_servers = novaservers.delete_servers(account_info['authtoken'], urls['nova'], to_delete_servers)

# Print the result of delete_servers
print "The results of delete servers : "
print deleted_servers

print "!!## -- Finished Tearing Down Virtualized Infrastructure -- ##!!"