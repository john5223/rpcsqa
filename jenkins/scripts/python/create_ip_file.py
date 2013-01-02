#!/usr/bin/python

""" Simple script to write our ip management file"""

import os, json

available_public_ips = []
for i in range(100, 199):
	available_public_ips.append('198.101.133.%d' % i)

current_env = {'num_servers' : 0, 'servers':{}}

razor_environment = {'available_public_ips': available_public_ips, 'current_env': current_env}

try:
	# Open the file
	fo = open("automated-razor-environment.json", "w")
except IOError:
	print "Failed to open file automated-razor-environment.json"
else:
	# Write the json string
	fo.write(json.dumps(razor_environment))

	#close the file
	fo.close()

	# print message for debugging
	print "automated-razor-environment.json successfully saved"