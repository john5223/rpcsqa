#!/usr/bin/python
import os
import json
import time
import argparse
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

parser = argparse.ArgumentParser()
parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--data_bag_location', action="store", dest="data_bag_loc", 
                    default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node", required=True, 
                    help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--display', action="store", dest="display", 
                    default="true", 
                    required=True, help="Display the node information only (will not reboot or teardown am)")

# Parse the parameters
results = parser.parse_args()

# converting string display only into boolean
if results.display == 'true':
    display = True
else:
    display = False

#############################################################
#Poll active models that match policy from given input
#   -- once policies are broker_* status then run nmap_chef_client
#############################################################

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

print "!!## -- Polling for  '%s'  active models --##!!" % policy
print "!!## -- Display only: %s --##!!" % results.display

get_active = False
while get_active == False:
    try:
        active_models = razor.simple_active_models(policy)
        get_active = True
    except:
        time.sleep(60)

if active_models:
    count = 0
    fail_count = 0
    active = False
    
    while not active and count < 15:
        count += 1               
        print "!!## -- Polling --##!!"
        active = True
        for a in active_models:
            data = active_models[a]
            curr_state = active_models[a]['current_state']
            if 'broker' not in curr_state:
                active = False
            else:
                if 'fail' in curr_state:                    
                    #Fix broker fail 
                    root_pass = ip = ''
                    try:
                        root_pass = data['root_password']
                        ip = data['eth1_ip']
                        am_uuid = data['am_uuid']
                        
                        # Remove active model
                        try:
                            print "!!## -- Removing active model %s --##!!" % am_uuid
                            delete = razor.remove_active_model(am_uuid)
                            print "!!## -- Deleted: %s " % delete
                        except Exception, e:
                            print "!!## -- Error removing active model: %s --##!!" % e
                            pass

                        #Restart via ssh
                        print "Trying to restart server with ip %s --##!!" % ip
                        try:
                            check_call_return = check_call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'reboot 0'" % (root_pass, ip), shell=True)
                            print "!!## -- Sucessfully restarted server with ip: %s --##!!" % ip
                        except CalledProcessError, cpe:
                            print "!!## -- Failed to restart server with ip: %s --##!!" % ip
                            print "!!## -- Return Code: %s --##!!" % cpe.returncode
                            print "!!## -- Command: %s --##!!" % cpe.cmd
                            print "!!## -- Output: %s --##!!" % cpe.output
                            fail_count +=1
                        time.sleep(600)                              
                    except Exception, e:
                        print "Couldn't fix broker fail: %s --##!!" % e
                        fail_count += 1
        
            if display:
                 temp = { 'am_uuid': active_models[a]['am_uuid'], 'current_state':  active_models[a]['current_state'] }
                 print json.dumps(temp, indent=4)
        
        time.sleep(30)
        active_models = razor.simple_active_models(policy)

    if fail_count > 0 or count >= 15:
        print "!!## -- One or more of the servers didnt reach broker_success status -- ##!!"
        for a in active_models:
            dbag_uuid = get_data_bag_UUID(active_models[a])
            ip = getip_from_data_bag(dbag_uuid)
            print "%s : %s " % (active_models[a]['am_uuid'], ip)
        sys.exit(1)

    else:    
        for a in active_models:
            dbag_uuid = get_data_bag_UUID(active_models[a])
            ip = getip_from_data_bag(dbag_uuid)
            print "%s : %s " % (active_models[a]['am_uuid'], ip)
            
        print "!!## -- Broker finished for %s -- ##!!" % policy
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)
    