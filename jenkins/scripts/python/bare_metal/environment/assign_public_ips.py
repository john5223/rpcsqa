#!/usr/bin/python

from razor_api import razor_api
from ssh_session import ssh_session
import argparse
import json
import os
import subprocess
import time

"""
	This script gathers information about the servers available to use via the razor 
	Author: Solomon Wagner
"""

# Gather the arguments from the command line
parser = argparse.ArgumentParser()

# Get the hostname for the alamo server
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
					required=True, help="IP for the Razor server")

parser.add_argument('--razor_username', action="store", dest="razor_username", 
					required=True, help="Username for the Razor server")

parser.add_argument('--razor_passwd', action="store", dest="razor_passwd", 
					required=True, help="Password for the username for the Razor server")

parser.add_argument('--os', action="store", dest="os",
					required=True, help="Type of operating system to be used")


# Parse the parameters
results = parser.parse_args()

# parse the razor environment file to get the current state of our razor environment
try:
	# Open the file
	fo = open("automated-razor-environment.json", "r")
except IOError:
	print "Failed to open file automated-razor-environment.json"
else:
	# Load the json string
	try:
		auto_razor_env = json.loads(fo.read())
	except ValueError:
		auto_razor_env = []

	#close the file
	fo.close()

	# print message for debugging
	print "automated-razor-environment.json successfully read into auto_razor_env"

# connect to the razor box
razor = razor_api(results.razor_ip)
print razor

# loop through the list of enviroments and assing the public ips
for server in auto_razor_env['current_env']['servers']:
	if results.os in auto_razor_env['current_env']['servers'][server]['status']:
		
		print json.dumps(auto_razor_env['current_env']['servers'][server], indent=2)

		print './assign_public_ip.sh -s %s -u %s -p %s -i %s -n %s -g %s -b %s -d %s' % (
					auto_razor_env['current_env']['servers'][server]['private_ip'],
					'root', 
					auto_razor_env['current_env']['servers'][server]['root_passwd'], 
					auto_razor_env['current_env']['servers'][server]['public_ip'], 
					'255.255.255.0', 
					'198.101.133.1', 
					'198.101.133.255', 
					'8.8.8.8'
				)

		"""
		subprocess.call([('./assign_public_ip.sh', '-s', '%s', '-u', '%s', '-p', '%s', '-i', '%s', '-n', '%s', '-g', '%s', '-b', '%s', '-d', '%s') % (
				auto_razor_env['current_env']['servers'][server]['private_ip'], 
				'root', 
				auto_razor_env['current_env']['servers'][server]['root_passwd'], 
				auto_razor_env['current_env']['servers'][server]['public_ip'], 
				'255.255.255.0', 
				'198.101.133.1', 
				'198.101.133.255', 
				'8.8.8.8'
			)], 
			shell=True
		)
		"""

		# Now that we gave a ready model with a private IP, we need to ssh into the Razor box and run assign_public_ip.sh
		session = ssh_session(results.razor_username, results.razor_ip, results.razor_passwd, True)

		# print the state of the current session
		print session

		# Now that we gave a ready model with a private IP, we need to ssh into the Razor box and run assign_public_ip.sh
		session.ssh('./assign_public_ip.sh -s %s -u %s -p %s -i %s -n %s -g %s -b %s -d %s' % (
					auto_razor_env['current_env']['servers'][server]['private_ip'], 
					'root', 
					auto_razor_env['current_env']['servers'][server]['root_passwd'], 
					auto_razor_env['current_env']['servers'][server]['public_ip'], 
					'255.255.255.0', 
					'198.101.133.1', 
					'198.101.133.255', 
					'8.8.8.8')
		)

		# print the state of the current session
		print session

		"""
		# wait for 10 seconds
		print '!!## -- Sleeping for 5 seconds'
		time.sleep(5)
		print 'Get back to work'
		"""
