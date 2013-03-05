#!/usr/bin/python
import os
import sys
import json
import time
import argparse
from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--data_bag_location', action="store", dest="data_bag_loc",
                    default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node", required=False, 
                    help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.3:4000", required=False, help="client for chef")

parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef")

parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/.chef/jenkins.pem", required=False, 
                    help="client pem for chef")

parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, 
                    help="Display the node information only (will not reboot or teardown am)")

# Save the parsed arguments
results = parser.parse_args()

# converting string display only into boolean
if results.display_only == 'true':
    display_only = True
else:
    display_only = False

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
    ans = None
    try:
        with open('%s/%s.json' % (data_bag_loc, uuid) ) as f: 
            ans = f.read()
        ans =  json.loads(ans)
        try:
            ip = ans['network_interfaces']['debian'][0]['address']
        except Exception, f:
            ip = ans['network_interfaces']['redhat'][0]['address']
        return str(ip)
    except IOError as e:
        print ans
        print e
        return ''
    except Exception, ee:
        print ans
        print ee
        raise Exception(ee)

def get_private_ip(chef_node_addresses):
    print "!!## -- %s -- ##!!" % chef_node_addresses
        for k, v in chef_node_addresses:
            print "!!## -- Key: %s -- Value: %s -- ##!!" % (k,v)
            for k2, v2 in v.iteritems():
                print "!!## -- Key2: %s -- Value2: %s -- ##!!" % (k2, v2)
                if v2 is 'inet':
                    print "Private IP: %s" % k
                    return k
                    break

#############################################################
#Collect active models that match policy from given input
#############################################################

razor = razor_api(results.razor_ip)
policy = results.policy

print "!!## -- Tearing down and rebooting  '%s'  active models -- ##!!" % policy
print "!!## -- Display only: %s -- ##!!" % results.display_only

active_models = razor.simple_active_models(policy)

#print json.dumps(active_models, indent=4)

if active_models:
    for active in active_models:
        data = active_models[active]
        private_ip = data['eth1_ip']
        am_uuid = data['am_uuid']
        chef_name = "%s%s.%s" % (data['hostname_prefix'], data['bind_number'], data['domain'])
        root_pass = getrootpass(data)
        dbag_uuid = get_data_bag_UUID(data)
        ip = getip_from_data_bag(dbag_uuid)
        
        if display_only:
            print "!!## -- Active Model ID: %s -- ##!!" % active
            print "!!## -- Data Bag UUID: %s -- ##!!" % dbag_uuid
            print "!!## -- Public address: %s -- ##!!" % ip
            print "!!## -- Chef Name: %s -- ##!!" % chef_name

            print "!!## -- Searching chef nodes -- ##!!"
            try:
                with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
                    node = Node(chef_name)
                    ip = node['ipaddress']
                    platform_family = node['platform_family']
                    print "!!## -- Node %s has platform_family: %s -- ##!!" % (chef_name, platform_family)
                    print "!!## -- Node %s network interfaces: -- ##!!" % chef_name
                    for interface in node['network']['interfaces']:
                        if platform_family == 'debian':
                            if 'eth1' in interface:
                                addresses = node['network']['interfaces']['%s' % interface]['addresses'].iteritems()
                                private_ip = get_private_ip(addresses)
                        elif platform_family == 'rhel':
                            if 'em2' in interface:
                                addresses = node['network']['interfaces']['%s' % interface]['addresses'].iteritems()
                                private_ip = get_private_ip(addresses)
                        else:
                            print "Platform not supported..."
                    print "!!## -- Node found %s, has ip %s -- ##!!" % (chef_name, ip)
            except Exception, e:
                print "!!## -- Error finding chef node %s -- ##!!" % chef_name
                print "!!## -- Exit with exception %s -- ##!!" % e
                pass
            
            print "!!## -- Searching chef clients -- ##!!"
            try:
                chef_api = ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client)
                client = chef_api.api_request('GET', '/clients/%s' % chef_name)
                print "Client: \n %s" % json.dumps(client, indent=4)
            except Exception, e:
                print "!!## -- Error printing chef clients: %s -- ##!!" % e
                pass 
        else: 
            print "!!## -- Removing active model -- ##!!"
            try:
                delete = razor.remove_active_model(am_uuid)
                print "Deleted: %s " % delete
                #pass
            except Exception, e:
                print "!!## -- Error removing active model: %s -- ##!!" % e
                pass

            print "!!## -- Removing chef-node -- ##!!"
            try:
                 with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
                    node = Node(chef_name)
                    if node is not None:
                        ip = node['ipaddress']
                        node.delete()
                    else:
                        pass
            except Exception, e:
                print "!!## -- Error removing chef node: %s -- ##!!" % e
                pass

            print "!!## -- Searching chef clients..."
            try:
                chef_api = ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client)
                if chef_api is not None:
                    response = chef_api.api_request('DELETE', '/clients/%s' % chef_name)
                    print "!!## -- Client %s removed with response: %s -- ##!!" % (chef_name, response)
                else:
                    pass
            except Exception, e:
                print "!!## -- Error removing chef node: %s -- ##!!" % e
                pass
            
            print "!!## -- Trying to restart server with ip %s -- ##!!" % ip
            try:
                check_call_return = check_call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'reboot 0'" % (root_pass, ip), shell=True)
                print "!!## -- Restart of server with ip: %s was a success -- ##!!" % ip
            except CalledProcessError, cpe:
                print "!!## -- Failed to restart server -- ##!!"
                print "!!## -- Private IP: %s, Public IP: %s -- ##!!" % (private_ip, ip)
                print "!!## -- Exited with following error status: -- ##!!"
                print "!!## -- Return code: %i -- ##!!" % cpe.returncode
                #print "!!## -- Command: %s -- ##!!" % cpe.cmd
                print "!!## -- Output: %s -- ##!!" % cpe.output
            
            print "!!## -- Sleeping for 30 seconds -- ##!!"
            time.sleep(30)
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!" % results.policy
    sys.exit(1)
