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

parser.add_argument('--data_bag_location', action="store", dest="data_bag_loc", 
                    #default="/home/john/git/rpcsqa/chef-cookbooks/data_bags/razor_node",
                    default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node", 
                    required=False, help="Policy to teardown from razor and reboot nodes")


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

def get_data_bag_UUID(data):
    try:
        eth = ['eth0_mac', 'eth1_mac', 'eth2_mac', 'eth3_mac' ]
        uuid = ''
        for e in eth:
            if e in data:
                uuid += data[e].replace(':','') + '_'
        return uuid[:-1]
    except:
        return ''
    

def getrootpass(data):
    if 'root_password' in data:
        return data['root_password']
    else:
        return ''
  
    
def getip_from_data_bag(uuid):
    try:
        data_bag_loc  = results.data_bag_loc
        with open('%s/%s.json' % (data_bag_loc, uuid) ) as f: 
            ans = f.read()
        ans =  json.loads(ans)
        ip = ans['network_interfaces']['debian'][0]['address']
        return str(ip)
    except IOError as e:
        print e
        return ''

#### MAIN ####
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
        time.sleep(60)



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
    
    count = 0
    active = False
    while active == False and count < 15:
        count += 1               
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

    if count < 15:    
        for a in active_models:
            dbag_uuid = get_data_bag_UUID(active_models[a])
            ip = getip_from_data_bag(dbag_uuid)
            print "%s : %s " % (active_models[a]['am_uuid'], ip)
            
        print "!!## -- Broker finished for %s -- ##!!" % policy

    else:
        print "!!## -- One or more of the servers didnt reach broker status -- ##!!"
        sys.exit(1)    