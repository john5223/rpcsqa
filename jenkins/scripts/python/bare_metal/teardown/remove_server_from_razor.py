#!/usr/bin/python

import os
import json
import argparse
from razor_api import razor_api

# Gather the arguments from the command line
parser = argparse.ArgumentParser()

# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
					required=True, help="IP for the Razor server")

parser.add_argument('--razor_username', action="store", dest="razor_username", 
					required=True, help="Username for the Razor server")

parser.add_argument('--razor_passwd', action="store", dest="razor_passwd", 
					required=True, help="Password for the username for the Razor server")

parser.add_argument('--public_ip', action="store", dest="public_ip", 
					required=True, help="IP for the Razor server")

# Parse the parameters
results = parser.parse_args()

try:
	# Open the file
	fo = open("automated-razor-environment.json", "r")
except IOError:
	print "Failed to open file automated-razor-environment.json"
else:
	# Write the json string
	razor_env = json.loads(fo.read())

	#close the file
	fo.close()

	# print message for debugging
	print "automated-razor-enviroment.json read successfully"

#print json.dumps(razor_env, indent=2)

removed = 0
for k1, v1 in razor_env['current_env']['servers'].items():
	for k2, v2 in v1.items():
		if k2 == 'public_ip':
			if v2 == results.public_ip:
				# open connection to razor and remove the active model
				razor = razor_api(results.razor_ip)
				print razor
				
				# remove the server from our environment file
				print "!!## -- Match found: uuid of active_model to delete : %s -- ##!!" % k1
				
				try:
					removed_server = razor.remove_active_model(k1)
					print json.dumps(removed_server, indent=2)
					if removed_server['status'] == 202:
						print "!!## -- Successfully removed following server from the active_models -- ##!!"
						print json.dumps(removed_server['content'], indent=2)
						razor_env['available_public_ips'].append(v2)
						razor_env['current_env']['num_servers'] -= 1
						del razor_env['current_env']['servers'][k1]
						removed += 1
					else:
						print "!!## -- Failed to remove server with active model uuid: %s --##!!" % k1
				except:
					print "!!## -- Something failed while trying to remove active model: %s -- ##!!" % k1
					
print "!!## -- removed : %s active model(s) -- ##!!" % removed

if removed == 0:
	print "!!## -- NO IP MATCHED -- ##!!"
else:
	try:
		# Open the file
		fo = open("automated-razor-environment.json", "w")
	except IOError:
		print "Failed to open file automated-razor-enviroment.json"
	else:
		# Write the json string
		fo.write(json.dumps(razor_env, indent=2))

		#close the file
		fo.close()

		# print message for debugging
		print "automated-razor-enviroment.json successfully saved"