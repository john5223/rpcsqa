#!/usr/bin/python
import json
import requests

""" Module to gather information about an account in NOVA """

def generate_account_info(url, username, password, tenantid):
	"""Generates a auth token, account number, and catalog info for the cloud account"""

	payload = {"auth":
			{"tenantName": tenantid,
			 "passwordCredentials": {"username": username, "password": password}
			}
		}
	# headers to send to the cloud servers auth
	headers = {'content-type': 'application/json'}

	# send auth request
	r = requests.post(url + '/v2.0/tokens', data=json.dumps(payload), headers=headers)

	# Load the returned content into a json object
	content = json.loads(r.content)
	
	# check the return content and return proper info
	if r.status_code == 200:
		# Save returned information
		account = content['access']['token']['tenant']['id']
		authtoken = content['access']['token']['id']
		catalogs = content['access']['serviceCatalog']

		# Create a dict to return
		account_info = {"authtoken" : authtoken, "account" : account, "catalogs" : catalogs}
		return account_info
	else:
		print "Error : " + content['error']['message'] 

def test_auth_token(authtoken):
	""" 
		Tests a auth token to see if it is still valid
		TODO: implement
	"""

	print "authtoken : %s" % (authtoken)


def urls(catalogs):
	""" Gets the endpoint urls for the cloud account """
	
	urls = {}
	for catalog in catalogs:
		urls[catalog['name']] = catalog['endpoints'][0]['publicURL']

	return urls

def images(url, authtoken):
	"""Returns a list of images that the cloud account can use"""

	# create the auth headers to talk to cloud servers for account
	headers = {'X-Auth-Token': authtoken, 'content-type': 'application/json'}

	# Gather list of images
	r = requests.get(url + '/images/detail', headers=headers)

	# Load the returned content into a json object
	content = json.loads(r.content)

	# Create a parsable dict with image name and ID that arent snapshots
	images = {}
	for image in content['images']:
		meta_data = image.get('metadata')
		if(meta_data.get('image_type') != 'snapshot'):
			images[image.get('name')] = image.get('id')

	return images

def flavors(url, authtoken):
	"""Returns a list of flavors that the cloud account can use"""
	
	# create the auth headers to talk to cloud servers for account
	headers = {'X-Auth-Token': authtoken, 'content-type': 'application/json'}
	
	# Call URL to get the flavors
	r = requests.get(url + '/flavors', headers=headers)

	# Load the returned content into a json object
	content = json.loads(r.content)
	
	# Create a dict of flavors indexed by size
	flavors = {}
	for flavor in content['flavors']:
		name = flavor.get('name')
		flavors[name.split(' ')[0]] = flavor.get('id')

	return flavors

def servers(url, authtoken):
	"""Returns a list of running servers on the account"""
	
	# create the auth headers to talk to cloud servers for account
	headers = {'X-Auth-Token': authtoken, 'content-type': 'application/json'}

	r = requests.get(url + '/servers/detail', headers=headers)

	# Load the returned content into a json object
	content = json.loads(r.content)

	servers = {}
	for server in content['servers']:
		name = server['name']
		serverid = server['id']
		status = server['status']
		private_ip = ''
		public_ip = ''
		
		if 'private' in server['addresses']:
			i = len(server['addresses']['private']) - 1
			while(i >= 0):
				if server['addresses']['private'][i]['version'] == 4:
					private_ip = server['addresses']['private'][i]['addr']
					break
				else:
					i = i - 1
		
		if 'public' in server['addresses']:
			i = len(server['addresses']['public']) - 1
			while(i >= 0):
				if server['addresses']['public'][i]['version'] == 4:
					public_ip = server['addresses']['public'][i]['addr']
					break
				else:
					i = i - 1

		servers[name] = {'id': serverid, 
						 'public_ip' : public_ip,
						 'private_ip' : private_ip,
						 'status' : status
						 }
	return servers
