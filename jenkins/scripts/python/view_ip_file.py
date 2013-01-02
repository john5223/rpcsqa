#!/usr/bin/python

""" Simple script to write our ip management file"""

import os, json

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
	print "automated-razor-environment.json read successfully"

print json.dumps(razor_env, sort_keys=True, indent=2)