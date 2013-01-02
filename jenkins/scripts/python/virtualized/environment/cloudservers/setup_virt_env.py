#!/usr/bin/python

import os
import json
import argparse
import subprocess
import cloudaccount
import cloudservers

"""
	This script will setup each one of the servers to run the Alamo ISO without actually running the ISO.
	It will need to assign a role to each machine, then from that role gather information about the server
	from the server. Once all the needed info is gathered, we will need to write a config file for each of the
	nodes based on roles via a template
"""

print "!!##-- Begin setup of cloud server enviroment --##!!"

# Gather the arguments from the command line
parser = argparse.ArgumentParser()

# Get the username for the Rackspace Public Cloud Account
parser.add_argument('--username', action="store", dest="username", 
					help="User name for the account")

parser.add_argument('--adminpass', action="store", dest= "adminpass",
					help="Password for the Verizon Dashboard admin user")

parser.add_argument('--osusername', action="store", dest= "osusername",
					help="Username for normal OpenStack user")

parser.add_argument('--osuserpass', action="store", dest= "osuserpass",
					help="Password for the normal OpenStack User")

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

try:
	# Open the file
	fo = open("%s-server-info.json" % (results.username), "r")
except IOError:
	print "Failed to open file %s-server-info.json" % (results.username)
else:
	# Write the json string
	server_info = json.loads(fo.read())

	#close the file
	fo.close()

	# print message for debugging
	print "%s-server-info.json successfully read into account_info" % (results.username)

# Loop through the json determining which server will be the controller and which will be the compute
for server in server_info:
	if '0' in server:
		server_info[server]['role'] = 'All-In-One'
	else:
		server_info[server]['role'] = 'Compute'

	server_info[server]['os_admin_passwd'] = results.adminpass
	server_info[server]['os_user_name'] = results.osusername
	server_info[server]['os_user_passwd'] = results.osuserpass

print json.dumps(server_info, sort_keys=True, indent=2)

print "!!##-- End setup of cloud server enviroment --##!!"

"""
Shell command to get ethernet interfaces

for i in `ip link sh | grep -P '^[0-9]: ' | sed 's/://g' | awk '{print $2}' | xargs`; do if [ `ip addr sh $i | grep '198.61.203.82' | wc -l` -gt 0 ]; then echo $i; fi; done
"""