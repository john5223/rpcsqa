#!/usr/bin/python
import os
import json
import argparse
from razor_api import razor_api
from ssh_session import ssh_session
import time
from chef import *


parser = argparse.ArgumentParser()
# Get the ip of the server you want to remove
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--data_bag_location', action="store", dest="data_bag_loc",
                    default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node", 
                    required=False, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--chef_url', action="store", dest="chef_url", 
                    default="http://198.101.133.4:4000", 
                    required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", 
                    default="jenkins", 
                    required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", 
                    default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem", 
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

razor = razor_api(results.razor_ip)
policy = results.policy

print "#################################"
print " Switching roles and running chef-client for  '%s'  active models" % policy
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


    hosts = []
    for active in active_models:
        data = active_models[active]
        
        #print data
        private_ip = data['eth1_ip']
        am_uuid = data['am_uuid']
        root_pass = getrootpass(data)
        dbag_uuid = get_data_bag_UUID(data)
        ip = getip_from_data_bag(dbag_uuid)

        if results.display_only == 'true':
            print "Active Model ID: %s " % active
            print "Data Bag UUID: %s " % dbag_uuid
            print "Public address: %s " % ip
            print "Private address: %s " % private_ip
            print ""

        try:
            session = ssh_session('root', ip, root_pass, False)
            host = session.ssh('hostname --fqdn')
            host = host.replace("\r\n","")
            hosts.append(host)
        except Exception, e:
            print "FAILURE: %s " % e
        finally:
            session.close()


    with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
        i = 0
        for host in hosts:

            # Get the node from chef
            node = Node(host)
            run_list = node.run_list
            environment = node.chef_environment

            if results.display_only == 'true':
                print "!!## -- %s has run list: %s, and environement: %s -- ##!!" % (node, run_list, environment)
            else:
                # set the environment and run lists
                print "!!## -- %s has run list: %s, and environement: %s -- ##!!" % (node, run_list, environment)
                environment = policy
                if i == 0:
                    print "!!## -- First host, set to controller -- ##!!"
                    run_list = ['qa-single-controller']
                elif i == 1:
                    print "!!## -- Second host, set to api -- ##!!"
                    run_list = ['qa-single-api']
                else:
                    print "!!## -- Set the rest of the hosts to compute  -- ##!!"
                    run_list = ['qa-single-compute']
                i += 1

                node.run_list = run_list
                node.chef_environment = environment

                try:
                    node.save()
                    print "!!## -- NODE: %s SAVED -- ##!!" % node
                except Exception, e:
                    print "!!## -- Failed to save node -- Exception: %s -- ##!!" % e
