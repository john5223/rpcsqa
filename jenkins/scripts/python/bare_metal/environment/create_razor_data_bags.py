#!/usr/bin/python
import os, json, argparse

def create_data_bag(ip, ident=None):

	ip_array = ip.split(".")
	
	if ident is None:
		data_bag = {
			"id": temp_ident,
			"network_interfaces": [
				{
					"auto": "true",
	    			"type": "static",
	    			"device": "eth0",
	    			"netmask": "255.255.255.0",
	    			"address": ip,
	    			"gateway": "%s.%s.%s.%s" % ( ip_array[0], ip_array[1], ip_array[2], 1)
				}
			]
		}

		try:
			# Open the file
			fo = open("%s.json" % ip, "w")
		except IOError:
			print "Failed to open file %s.json" % ip
		else:
			# Write the json string
			fo.write(json.dumps(data_bag, indent=4))

			#close the file
			fo.close()

			# print message for debugging
			print "%s.json successfully saved" % ip
	else:
		data_bag = {
			"id": ident,
			"network_interfaces": [
				{
					"auto": "true",
	    			"type": "static",
	    			"device": "eth0",
	    			"netmask": "255.255.255.0",
	    			"address": ip,
	    			"gateway": "%s.%s.%s.%s" % ( ip_array[0], ip_array[1], ip_array[2], 1)
				}
			]
		}

		try:
			# Open the file
			fo = open("%s.json" % ident, "w")
		except IOError:
			print "Failed to open file %s.json" % ident
		else:
			# Write the json string
			fo.write(json.dumps(data_bag, indent=4))

			#close the file
			fo.close()

			# print message for debugging
			print "%s.json successfully saved" % ident


# MAIN PROGRAM

# Gather the arguments from the command line
parser = argparse.ArgumentParser()

# Path to JSON file of MACs
parser.add_argument('--file_path', action="store", dest="file_path", 
					required=True, default=None, help="Path to the JSON file")

# Parse the parameters
results = parser.parse_args()

path = os.path.abspath(results.file_path)

print path
#open JSON file
try:
	fo = open(path, 'r')
except IOError:
		print "Failed to open file @ %s" % path
else:
	print fo
	macs_to_ips = json.loads(fo.read())
	fo.close()

for k,v in macs_to_ips.items():
	print "key: %s, value: %s" % (k,v)
	create_data_bag(v, k)
"""
if results.end_ip is None:
	create_data_bag(results.start_ip, results.ident)
else:
	(size, start, end) = check_addr(results.start_ip, results.end_ip)
	if size < 1:
		print "Size doesnt work, check ip addresses"
	else:
		for i in range(int(start[3]),int(end[3])):
			ip = "%s.%s.%s.%s" % (start[0], start[1], start[2], i)
			if results.ident is None:
				create_data_bag(ip)
			else:
				create_data_bag(ident, ip)
"""
