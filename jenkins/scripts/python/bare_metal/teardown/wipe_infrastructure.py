import os
import json
import argparse
from razor_api import razor_api
from ssh_session import ssh_session

# Run Things
print "!!## -- Wiping Bare Metal Infrastructure -- ##!!"

# Gather the arguments from the command line
parser = argparse.ArgumentParser()

# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
					required=True, help="IP for the Razor server")

parser.add_argument('--razor_username', action="store", dest="razor_username", 
					required=True, help="Username for the Razor server")

parser.add_argument('--razor_passwd', action="store", dest="razor_passwd", 
					required=True, help="Password for the username for the Razor server")

# Parse the parameters
results = parser.parse_args()

# Connect to razor
razor = razor_api(results.razor_ip)
print razor

# Collect all active models
active_models = razor.simple_active_models()

# Loop through the active models and collect them
reboot = []
session = ssh_session(results.razor_username, results.razor_ip, results.razor_passwd, True)
for k,v in active_models.items():
	# do a ping to make sure each box is alive
	output = session.ssh('ping -c 5 %s' % v['eth1_ip'])
	print "!!## -- length of last ping: %s -- ##!!" % len(output)
	if len(output) > 1:
		# if ping came back good, remove the active model
		try:
			result = razor.remove_active_model(v['am_uuid'])
			if result.status != 202:
				reboot.append({'am_uuid': v['am_uuid'], 
							   'root_password': v['root_password'], 
							   'eth1_ip': v['eth1_ip'], 
							   'status': 'failed',
							   'failure': 'active_model'})
			else:
				reboot.append({'am_uuid': v['am_uuid'], 
					 		   'root_password': v['root_password'], 
					 		   'eth1_ip': v['eth1_ip'],
					 		   'status': 'am_removed'})
		except:
			pass
	
	else:
		reboot.append({'am_uuid': v['am_uuid'], 
				       'root_password': v['root_password'], 
				     	'eth1_ip': v['eth1_ip'], 
				     	'status': 'failed',
				     	'failure': 'ping_check'})

session.close()

# Loop through the successfill am removals and reboot the machines
session2 = ssh_session(results.razor_username, results.razor_ip, results.razor_passwd, True)
i=0
for machine in reboot[:]:
	if(machine['status'] == 'am_removed'):
		try:
			session2.ssh("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -l root %s 'reboot'" % (
				machine['root_password'], machine['eth1_ip']))
		except:
			machine['status'] = 'failed'
			machine['failure'] = 'reboot'
		else:
			machine['status'] = 'passed'
	else:
		pass

	reboot[i] = machine
	i += 1

session2.close()

print "!!## -- REBOOT RESULTS -- ##!!"
print json.dumps(reboot, indent=2)

print "!!## -- End Wipe Infrastructure -- ##!!"
