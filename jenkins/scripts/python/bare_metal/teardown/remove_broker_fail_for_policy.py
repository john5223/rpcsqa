#!/usr/bin/python
import os
import sys
import time
import argparse
import subprocess
from razor_api import razor_api

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()

parser.add_argument('--razor_ip', action="store", dest="razor_ip", 
                    required=True, help="IP for the Razor server")

parser.add_argument('--policy', action="store", dest="policy", 
                    required=True, help="Policy to teardown from razor and reboot nodes")

parser.add_argument('--display_only', action="store", dest="display_only", 
                    default="true", 
                    required=False, help="Display the node information only, dont remove or reboot")


# Save the parsed arguments
results = parser.parse_args()

# converting string display only into boolean
if results.display_only == 'true':
    display_only = True
else:
    display_only = False

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
print "Display only: %s " % results.display_only

got_active = False
attempt = 0
while not got_active and attempt < 5:
    try:
        active_models = razor.simple_active_models(policy)
        attempt += 1
        got_active = True
    except:
        time.sleep(60)

if active_models:
    failed_restart = 0
    for active in active_models:
        data = active_models[active]
        am_uuid = data['am_uuid']
        curr_state = data['current_state']
        
        if 'broker_fail' in curr_state:
            root_pass = get_root_pass(data)
            ip = data['eth1_ip']
            
            if results.display_only == 'true':
                print "Active Model ID: %s " % active
                print "IP address: %s " % ip
            else:
                print "Removing active model..."
                try:
                    delete = razor.remove_active_model(am_uuid)
                    print "Deleted: %s " % delete
                except Exception, e:
                    print "Error removing active model: %s " % e
                    pass

                print "Trying to restart server with ip %s...." % ip
                try:
                    return_code = subprocess.call("sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root %s 'reboot 0'" % (root_pass, ip), shell=True)

                    if return_code != 0:
                        print "Error: Could not restart."
                        failed_restart += 1
                    else:
                        print "Restart success."

                except Exception, e:
                    print "Restart FAILURE: %s " % e
                    pass

                print "Sleeping for 30 seconds..."
                time.sleep(30)
        else:
            print "Active Model %s is not in broker_fail state, but in %s, skipping" % (am_uuid, curr_state)

    if failed_restart > 0:
        sys.exit(1)
else:
    # No active models for the policy present, exit.
    print "!!## -- Razor Policy %s has no active models -- ##!!"
    sys.exit(1)
    