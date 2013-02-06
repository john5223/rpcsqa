#!/usr/bin/python
import os
import json
import argparse
from razor_api import razor_api
import time

parser = argparse.ArgumentParser()
# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--display', action="store", dest="display", 
                    default="true", 
                    required=False, help="Display the node information only (will not reboot or teardown am)")


# Parse the parameters
results = parser.parse_args()

#############################################################
#Poll active models that match policy from given input
#   -- once policies are broker_* status then run nmap_chef_client
#############################################################

#### METHODS ####
def get_root_pass(data):
    if 'root_password' in data:
        return data['root_password']
    else:
        return ''

#### MAIN ####
razor = razor_api(results.razor_ip)
policy = results.policy

print "#################################"
print "Polling for  '%s'  active models" % policy
print "Display only: %s " % results.display


got_active = False
while got_active == False:
    try:
        active_models = razor.simple_active_models(policy)
        got_active = True
    except:
        time.sleep(60)

if active_models == {}:
    print "'%s' active models: 0 " % (policy)
    print "#################################"
else:
    if 'response' in active_models.keys():
        active_models = active_models['response']
    
    print "'%s' active models: %s " % (policy, len(active_models))
    print "#################################" 
    
    for a in active_models:
        
        data = active_models[a]
        am_uuid = data['am_uuid']
        curr_state = data['current_state']
        
        if 'broker_fail' in curr_state:
            root_password = get_root_pass(data)
            ip = data['eth1_ip']
            
            print "Removing active model..."
            try:
                delete = razor.remove_active_model(am_uuid)
                print "Deleted: %s " % delete
            except Exception, e:
                print "Error removing active model: %s " % e
                pass

            print "Trying to restart server with ip %s...." % ip
            try:
                subprocess.call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'reboot 0'" % (root_pass, ip), shell=True)
                print "Restart success."
            except Exception, e:
                print "Restart FAILURE: %s " % e
                pass

            print "Sleeping for 15 seconds..."
            time.sleep(15)
        else:
            print "Active Model %s is not in broker_fail state, but in %s, skipping" % (am_uuid, curr_state)