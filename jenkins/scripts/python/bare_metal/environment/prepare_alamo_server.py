#!/usr/bin/python

import os
import subprocess
import argparse
from ssh_session import ssh_session

"""
	This script connects to our blank ubuntu server and dl's and runs the set-up bash.
	Author: Solomon Wagner
"""

# Gather the arguments from the command line
parser = argparse.ArgumentParser()

# Get the hostname for the alamo server
parser.add_argument('--host_name', action="store", dest="host_name", 
					required=True, help="Hostname/IP for the Server")

# Get the username for the host
parser.add_argument('--user_name', action="store", dest="user_name", 
					required=True, help="Non-root user name for the host")

# Get the password for the host
parser.add_argument('--user_passwd', action="store", dest="user_passwd", 
					required=True, help="Non-root password for the host")

# Get the password for the host
parser.add_argument('--v', action="store", dest="verbose", 
					default=True, help="Verbose")

# Parse the parameters
results = parser.parse_args()

# Connect to the host
my_session = ssh_session(results.user_name, results.host_name, results.user_passwd, results.verbose)

# scp the setup file to the server
my_session.scp('/var/lib/jenkins/workspace/PCQARepo/scripts/bash/prepare-alamo-server.sh', '')

#Changing permissions to 0755 on prepare-alamo-server.sh
my_session.ssh('chmod 0755 ./prepare-alamo-server.sh')

# scp the rpcs.cfg file to the server
my_session.scp('/var/lib/jenkins/workspace/Config-Alamo-Server/%s-rpcs.cfg' % results.host_name, '')

# scp the functions.sh script to the server
my_session.scp('/var/lib/jenkins/workspace/Update-Alamo-Builder/rpcs/functions.sh', '')

# scp the late_command.sh script to the server
my_session.scp('/var/lib/jenkins/workspace/Update-Alamo-Builder/rpcs/late_command.sh', '')

# scp the status.sh script to the server
my_session.scp('/var/lib/jenkins/workspace/Update-Alamo-Builder/rpcs/status.sh', '')

# scp the status.rb script to the server
my_session.scp('/var/lib/jenkins/workspace/Update-Alamo-Builder/rpcs/status.rb', '')

# scp the post-install.sh script to the server
my_session.scp('/var/lib/jenkins/workspace/Update-Alamo-Builder/rpcs/post-install.sh', '')

# Close the SSH Session
my_session.close()

print "!!## -- Setup for Bare Metal Finished -- ##!!"