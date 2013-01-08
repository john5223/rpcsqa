#!/usr/bin/python
import os
import json
import argparse
from razor_api import razor_api
from ssh_session import ssh_session
import time

parser = argparse.ArgumentParser()
# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--data-bag-location', action="store", dest="data_bag_loc", 
                    #default="/home/john/git/rpcsqa/chef-cookbooks/data_bags/razor_node",
                    default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node", 
                    required=False, help="Policy to teardown from razor and reboot nodes")


parser.add_argument('--display-only', action="store", dest="display_only", 
                    default="true", 
                    required=False, help="Display the node information only (will not reboot or teardown am)")


# Parse the parameters
results = parser.parse_args()



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
    data_bag_loc  = results.data_bag_loc
    try:
        with open('%s/%s.json' % (data_bag_loc, uuid) ) as f: 
            ans = f.read()
        ans =  json.loads(ans)
        ip = ans['network_interfaces'][0]['address']
        return str(ip)
    except IOError as e:
        print e
        return ''


#############################################################
#Collect active models that match policy from given input
#############################################################

#####



razor = razor_api(results.razor_ip)
policy = results.policy


print "#################################"
print "Tearing down and rebooting  '%s'  active models" % policy


active_models = razor.simple_active_models(policy)


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
    for active in active_models:
        data = active_models[active]
        
        #print data
        private_ip = data['eth1_ip']
        am_uuid = data['am_uuid']
        root_pass = getrootpass(data)
        dbag_uuid = get_data_bag_UUID(data)
        ip = getip_from_data_bag(dbag_uuid)
        
        

        #Remove active model
        
        #SSH into ip and reboot 
        
        print "Active Model ID: %s " % active
        print "Data Bag UUID: %s " % dbag_uuid
        print "ROOT_PASS: %s " % root_pass
        print "Public address: %s " % ip
        print "Private address: %s " % private_ip
        print ""
        
        
        if results.display_only == 'false':
            
            print "Removing active model..."
            try:
                delete = razor.remove_active_model(am_uuid)
                print "Deleted: %s " % delete
                #pass
            except Exception, e:
                print "Error removing active model: %s " % e
                continue
            
            print "Trying restart...."
            try:
                session = ssh_session('root', ip, root_pass, False)
                #session.ssh('reboot 0')
                print "Restart success."
            except Exception, e:
                print "Restart FAILURE: %s " % e
            finally:
                session.close()
            
            
            print "Sleeping for 5 seconds..."
            time.sleep(5)
            print "#################################"
            
        
        
        
     
     
        