#!/usr/bin/python
import os, json, argparse

temp_ident = "123456789012_123456789012_123456789012_123456789012"

def check_addr(start_a, end_a):

	start_addr = start_a.split(".")
	end_addr = end_a.split(".")

	end_int = int(end_addr[3])
	start_int = int(start_addr[3])

	size = end_int - start_int
	return (size, start_addr, end_addr) 

def create_data_bag(ident=None, ip):
	if ident is None:
		data_bag = {
			"id": temp_ident,
			"network_interfaces": [
				{
					"auto": "true",
	    			"type": "static",
	    			"device": "eth0",
	    			"netmask": "255.255.255.0",
	    			"address": ip
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
	    			"address": ip
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

# Get the start of the ip range
parser.add_argument('--start_ip', action="store", dest="start_ip", 
					required=True, help="Starting IP address")

# Get the ending of the ip range
parser.add_argument('--end_ip', action="store", dest="end_ip", 
					required=True, help="Ending IP address")

# Get the identity of the box
parser.add_argument('--ident', action="store", dest="ident", 
					required=False, defaut=None, help="Identy of the box (UUID of MACs)")

# Parse the parameters
results = parser.parse_args()

(size, start, end) = check_addr(results.start_ip, results.end_ip)

if size < 0:
	print "Size doesnt work, check ip addresses"
else:
	for i in range(int(start[3]),int(end[3])):
		ip = "%s.%s.%s.%s" % (start[0], start[1], start[2], i)
		if results.ident is None:
			create_data_bag(ip)
		else:
			create_data_bag(ident, ip)
