import json
import requests
import base64

def build_servers(authtoken, url, name, numservers, osimageref, osimagename, projectname, flavor, personalities=None, keyname=None):
	"""
		Creates numservers amount of servers and returns the list of created servers
	"""

	servers = []
	for i in range(int(numservers)):
		server = build_server(authtoken, url, name + ' ' + str(i), osimageref, osimagename, projectname, flavor, personalities, keyname)
		servers.append(server)

	return servers

def build_server(authtoken, url, name, osimageref, osimagename,  projectname, flavor, personalities=None, keyname=None):
	"""
		Builds a new server on the account using the api for the give url
	"""
	# print for debugging
	#print ("name : %s, url : %s, osimageref : %s, osimagename: %s, project : %s, flavor : %s" 
	#	   % (name, url, osimageref, osimagename, projectname, flavor))

	# build json to submit
	build = {
		"server": 
			{
			"name" : name, 
			"imageRef" : osimageref, 
			"flavorRef" : flavor, 
			"metadata" : 
				{
					"My Server Name" : osimagename
				},
			"key_name" : keyname,
			"personality" : personalities
			}
		}

	# submit call to public cloud api to build server
	data = build
	headers = {'X-Auth-Token': authtoken, 'content-type': 'application/json', 'X-Auth-Project-Id' : projectname}
	r = requests.post(url + '/servers', data=json.dumps(data), headers=headers)

	content = json.loads(r.content)
	return content

def delete_servers(authtoken, url, serverids):
	"""
		Delete a list of servers by ids
	"""

	success = []
	failed = []
	for serverid in serverids:
		status_code = delete_server(authtoken, url, serverid)
		if status_code == 204:
			success.append(serverid)
		else:
			failed.append(serverid)

	return {'success' : success, 'failed' : failed}

def delete_server(authtoken, url, serverid):
	"""
		Deletes a given server with id
	"""

	print url + '/servers/%s' % serverid
	headers = {'X-Auth-Token': authtoken, 'content-type': 'application/json'}
	r = requests.delete(url + '/servers/%s' % serverid, headers=headers)

	return r.status_code

def add_personalities(personalities):
	"""Loops through the passed personalities and adds them to the personalities"""
	pers = []

	# Loop through the passed personalities and build the dict that NOVA expects
	for per in personalities:
		pers.append(add_personality(per['path'], per['filename']))

	return pers

def add_personality(path, filename):
	""" Adds the personalities that we want right now, will make this take in parameters later"""

	per = {}
	try:
		# Open the file
		fo = open(filename)
	except IOError:
		print "Failed to open file %s" % (filename)
	else:
		# Open the file and convert its contents to base64
		fo_contents = fo.read()
		fo_contents_64 = base64.b64encode(fo_contents)
		per['path'], per['contents'] = path, fo_contents_64
		
	return per

