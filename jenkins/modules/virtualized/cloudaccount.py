import json
import requests

def generate_account_info(username, apikey):
	"""
		Generates a auth token, account number, and catalog info for the cloud account
	"""

	payload = {"auth":
			{"RAX-KSKEY:apiKeyCredentials":
				{"username": username, "apiKey": apikey} 
			} 
		}
	# headers to send to the cloud servers auth
	headers = {'content-type': 'application/json'}

	# send auth request
	r = requests.post('https://auth.api.rackspacecloud.com/v2.0/tokens', data=json.dumps(payload), headers=headers)

	# Load the returned content into a json object
	content = json.loads(r.content)
	
	# Save returned information
	account = content['access']['token']['tenant']['id']
	authtoken = content['access']['token']['id']
	catalogs = content['access']['serviceCatalog']

	# Create a dict to return
	account_info = {"authtoken" : authtoken, "account" : account, "catalogs" : catalogs}
	return account_info

def test_auth_token(authtoken):
	""" 
		Tests a auth token to see if it is still valid
		TODO: implement
	"""

	print "authtoken : %s" % (authtoken)


def urls(catalogs):
	"""
		Gets the endpoint urls for the cloud account
	"""

	for catalog in catalogs:
		for endpoint in catalog['endpoints']:
			if('servers' in endpoint.get('publicURL')) and ('2' in endpoint.get('versionId')):
				if('dfw' in endpoint.get('publicURL')):
					## Save the dfw endpint if it exists
					dfw_url = endpoint.get('publicURL')
				elif('ord' in endpoint.get('publicURL')):
					## Save the ord endpoint if it exists
					ord_url = endpoint.get('publicURL')
				else:
					## do nothing with the others
					other_urls += endpoint.get('publicURL')

	urls = {"dfw" : dfw_url, "ord" : ord_url}
	return urls

def images(url, authtoken):
	"""
		Returns a list of images that the cloud account can use
	"""

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

	"""
		Returns a list of flavors that the cloud account can use
	"""
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
	"""
		Returns a list of running servers on the account
		TODO: implement
	"""
	#print "URL : %s, authtoken : %s" % (url, authtoken)
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
		
		i = len(server['addresses']['private']) - 1
		while(i >= 0):
			if server['addresses']['private'][i]['version'] == 4:
				private_ip = server['addresses']['private'][i]['addr']
				break
			else:
				i = i - 1
		
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
