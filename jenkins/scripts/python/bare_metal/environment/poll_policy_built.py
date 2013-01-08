#!/usr/bin/python
import os
import json
import argparse
from razor_api import razor_api
import time

import sys
sys.stdout.flush()


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

#####



razor = razor_api(results.razor_ip)
policy = results.policy


print "#################################"
print "Polling for  '%s'  active models" % policy
print "Display only: %s " % results.display


get_active = False
while get_active == False:
    try:
        active_models = razor.simple_active_models(policy)
        get_active = True
    except:
        pass



if active_models == {}:
    print "'%s' active models: 0 " % (policy)
    print "#################################"
else:
    
    
    if 'response' in active_models.keys():
        active_models = active_models['response']
    
    print "'%s' active models: %s " % (policy, len(active_models))
    print "#################################"

    #For each active model
        #get root password 
        #find uuid from MAC addresses
        #get data bag for that key to get ip
        #remove specific active model by uuid
        #ssh into ip and reboot   
    
    
    
    active = False
    while active == False:
        print "Polling..."
        active = True
        for a in active_models:
            if 'broker_' not in active_models[a]['current_state']:
                active = False
                pass 
            if results.display == "true":
                 temp = { 'am_uuid': active_models[a]['am_uuid'], 'current_state':  active_models[a]['current_state'] }
                 print json.dumps(temp, indent=4)
        
        time.sleep(30)
        active_models = razor.simple_active_models(policy)
          
    print "Broker finished for %s " % policy
     
        