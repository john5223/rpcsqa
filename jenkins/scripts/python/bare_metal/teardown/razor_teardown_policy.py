#!/usr/bin/python
import os
import subprocess
import json
import argparse
from razor_api import razor_api
import time

from chef import *

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

parser.add_argument('--chef_url', action="store", dest="chef_url", 
                    default="http://198.101.133.3:4000", 
                    required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", 
                    default="jenkins", 
                    required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", 
                    default="/var/lib/jenkins/.chef/jenkins.pem", 
                    required=False, help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", 
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
print "Display only: %s " % results.display_only

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
        chef_name = "%s%s.%s" % (data['hostname_prefix'], data['bind_number'], data['domain'])
        root_pass = getrootpass(data)
        dbag_uuid = get_data_bag_UUID(data)
        # get the ip from the data bag
        ip = getip_from_data_bag(dbag_uuid)

        # check to see if box has a chef node and client
        try:
            chef_api = ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client)
            chef_node = chef_api.api_request('GET', '/nodes/%s' % chef_name)
            chef_client = chef_api.api_request('GET', '/clients/%s' % chef_name)
            # if chef has a node for this box, change the ip to the ip that chef has for it
            #print json.dumps(chef_node, indent=4)
            ip = chef_node['ipaddress']
        except Exception, e:
            print "Razor node %s doesnt have a chef node / chef client, exception %s" % (chef_name, e)
            continue
        
        if results.display_only == 'true':
            print "Active Model ID: %s " % active
            print "Data Bag UUID: %s " % dbag_uuid
            print "Public address: %s " % ip
            print "Private address: %s " % private_ip
            print "Chef Name: %s" % chef_name
            print "Searching chef clients..."
            if chef_client is not None and chef_node is not None:
                print "Chef Node: \n %s" % json.dumps(chef_node, indent=4)
                print "Client: \n %s" % json.dumps(chef_client, indent=4)
            else:
                print "Razor node %s doesnt have a chef client or node" % chef_name
        else: 
            print "Removing active model..."
            try:
                delete = razor.remove_active_model(am_uuid)
                print "Deleted: %s " % delete
                #pass
            except Exception, e:
                print "Error removing active model: %s " % e
                continue

            print "Attempting to remove Chef node %s..." % chef_name
            if chef_node is not None:
                try:
                    print "Removing chef-node %s..." % chef_name
                    chef_node.delete()
                except Exception, e:
                    print "Error removing chef node: %s " % e
                    continue 

            print "Attempting to remove chef client %s..." % chef_name
            if chef_client is not None:
                try:
                    response = chef_api.api_request('DELETE', '/clients/%s' % chef_name)
                    print "Client %s removed with response: %s" % (chef_name, response)
                except Exception, e:
                    print "Error removing chef client: %s " % e
                    continue
            
            print "Trying to restart server %s with ip %s...." % (chef_name, ip)
            try:
                subprocess.call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'reboot 0'" % (root_pass, ip), shell=True)
                print "Restart success."
            except Exception, e:
                print "Restart FAILURE: %s " % e
            
            
            print "Sleeping for 10 seconds..."
            time.sleep(10)
            print "#################################"
