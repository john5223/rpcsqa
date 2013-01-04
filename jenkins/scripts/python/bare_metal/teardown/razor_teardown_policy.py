#!/usr/bin/python
import os
import json
import argparse
from razor_api import razor_api

parser = argparse.ArgumentParser()
# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--data-bag-location', action="store", dest="data_bag_loc", 
                    default="/home/john/git/rpcsqa/chef-cookbooks/data_bags/razor_node", 
                    required=False, help="Policy to teardown from razor and reboot nodes")
# Parse the parameters
results = parser.parse_args()









def get_data_bag_UUID(data):
    try:
            
        eth = ['eth0_mac', 'eth1_mac', 'eth2_mac', 'eth3_mac' ]
        uuid = ''
        for e in eth:
            if e in data:
                uuid = data[e].replace(':','') + '_'
        return uuid[:-1]
    except:
        return ''
    
    

def getrootpass(data):
    if 'root_password' in data:
        return data['root_password']
    else:
        return ''
  
    
def getip_from_data_bag(uuid):
    data_bag_loc  = results.data_bag_loc
    try:
        with open('%s/%s.json' % (data_bag_loc, uuid) ) as f: 
            ans = f.read()
        ans =  json.loads(ans)
        ip = ans['network_interfaces'][0]['address']
        return str(ip)
    except IOError as e:
        return ''


#Collect active models that match policy from args
razor = razor_api(results.razor_ip)
policy = results.policy

active_models = razor.simple_active_models(policy)

if active_models == {}:
    print "'%s' active models: 0 " % (policy)
else:
    if 'response' in active_models.keys():
        active_models = active_models['response']
    
    print "'%s' active models: %s " % (policy, len(active_models))
    
    
    
    #For each active model
        #get root password 
        #find uuid from MAC addresses
        #get data bag for that key to get ip
        #remove specific active model by uuid
        #ssh into ip and reboot   
    for active in active_models:
        data = active_models[active]

        uuid = get_data_bag_UUID(data)
        root_pass = getrootpass(data)
        ip = getip_from_data_bag(uuid)

        #Remove active model
        
        #SSH into ip and reboot 
        
        print "##################"
        print active
        print "##################"
        
        #print data
        print "UUID: %s " % uuid
        print "ROOT_PASS: %s " % root_pass
        print "Ip address: %s " % ip
        
        
        print "############################################"
        print ""
     
     
        