#!/usr/bin/python

from razor_api import razor_api
from ssh_session import ssh_session
import argparse
import json
import os

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

parser.add_argument('--num_servers', action="store", dest="num_servers",
					required=True, help="The number of servers to be used")

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

print json.dumps(auto_razor_env['current_env'], sort_keys=True, indent=2)

# connect to the razor box
razor = razor_api(results.razor_ip)
print razor

print "!!## -- FINDING %s SERVER(S) VIA RAZOR -- ##!!" % results.num_servers

# Talk to our razor api to gather a list of available models
#print "!!## -- Available Nodes -- ##!!"
#print json.dumps(razor.nodes(), indent=2)

# Talk to our razor api to gather a list of available models
#print "!!## -- Available Templates -- ##!!"
#print json.dumps(razor.model_templates(), indent=2)

# Talk to our razor api to gather a list of available models
#print "!!## -- Available Models -- ##!!"
#print json.dumps(razor.simple_models(), indent=2)

#print json.dumps(razor.active_models(), indent=2)
# Talk to the razor api to gather a list of active models
#print "!!## -- Active Models -- ##!!"
active_models = razor.simple_active_models()
#print json.dumps(active_models, indent=2)

# Talk to the razor api to get a list of ready active_models
#print "!!## -- Ready Servers -- ##!!"
ready_servers = razor.broker_success(active_models)
#print json.dumps(ready_servers, indent=2)

print "!!## -- Number of Servers in Complete or Post Status : %i -- ##!!" % len(ready_servers)

# Loop through the ready models and grab one
i = 0
used_servers = 0
num_servers = int(results.num_servers)

for server in ready_servers:
	print "!!## -- Number of servers left to find %i -- ##!!" % num_servers
	print "!!## -- Trying Active Model with UUID: %s and status: %s" % (server['am_uuid'], server['description'])
	if results.os in server['description'] and server['am_uuid'] not in auto_razor_env['current_env']['servers'] and num_servers >= 0:		
		print "!!## -- FOUND A MATCHING OS WITH A PRIVATE IP NOT ALREADY IN USE-- ##!!"
		print '%s : %s' % (results.os, server['description'])

		to_use_private_ip = server['eth1_ip_addr']
		to_use_public_ip = auto_razor_env['available_public_ips'].pop()

		server_env = {}
		for k,v in server.items():
			server_env[k] = v
		
		server_env['public_ip'] = to_use_public_ip

		auto_razor_env['current_env']['servers'][server['am_uuid']] = server_env
		
		#print json.dumps(to_use_server, indent=2)
		print "!!## -- PUBLIC: " + to_use_public_ip + ", PRIVATE : " + to_use_private_ip + ", UUID OF ACTIVE MODEL : " + server['am_uuid'] + " -- ##!!"

		num_servers -= 1
		used_servers += 1

	else:
		# server didnt match criteria, on to the next
		print "!!## -- Server didnt match os %s or already exists in enviroment file -- ##!!" % results.os

	if num_servers == 0:
		break

	
auto_razor_env['current_env']['num_servers'] += used_servers

if used_servers != int(results.num_servers):
	print "!!## -- FAILED TO ALLOCATE %i SERVERS -- ##!!" % (int(results.num_servers) - used_servers)

# If we didnt find a server let the user know
if used_servers < 1:
	print "!!## -- DIDN'T FIND A SUITABLE SERVER -- ##!!"
else:
	# update the PCQA JSON / DB
	try:
		# Open the file
		fo = open("automated-razor-environment.json", "w")
	except IOError:
		print "Failed to open file automated-razor-environment.json"
	else:
		# Write the json string
		fo.write(json.dumps(auto_razor_env, indent=2))

		#close the file
		fo.close()

		# print message for debugging
		print "automated-razor-environment.json successfully saved"
