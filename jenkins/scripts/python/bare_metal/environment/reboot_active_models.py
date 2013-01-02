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
#print json.dumps(active_models, indent=2)

# Loop through the active models and collect them
session = ssh_session(results.razor_username, results.razor_ip, results.razor_passwd, True)
reboot = []
for k,v in active_models.items():
	# do a ping to make sure each box is alive
	output = session.ssh('ping -c 5 %s' % v['eth1_ip'])
	if len(output) > 1:
		reboot.append({'am_uuid': v['am_uuid'], 
					   'root_password': v['root_password'], 
					   'eth1_ip': v['eth1_ip'],
					   'status': 'ping_good'})
	else:
		reboot.append({'am_uuid': v['am_uuid'], 
					   'root_password': v['root_password'], 
					   'eth1_ip': v['eth1_ip'],
					   'status': 'ping_bad'})

print json.dumps(reboot, indent=2)
session.close()

# Loop through the successfill am removals and reboot the machines
session2 = ssh_session(results.razor_username, results.razor_ip, results.razor_passwd, True)
i = 0
for machine in reboot[:]:
	if(machine['status'] == 'ping_good'):
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