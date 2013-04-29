import sys
import time
from razor_api import razor_api
from server_helper import run_remote_ssh_cmd

razor_ip = '198.101.133.3'
razor = razor_api(razor_ip)


def remove_broker_fail(policy):
    active_models = razor.simple_active_models(policy)
    for active in active_models:
        data = active_models[active]
        if 'broker_fail' in data['current_state']:
            print "!!## -- Removing active model  (broker_fail) -- ##!!"
            root_pass = razor.get_active_model_pass(
                data['am_uuid'])['password']
            ip = data['eth1_ip']
            run = run_remote_ssh_cmd(ip, 'root', root_pass, 'reboot 0')
            if run['success']:
                razor.remove_active_model(data['am_uuid'])
                time.sleep(15)
            else:
                print "Trouble removing broker fail"
                print run
                sys.exit(1)


def razor_password(node):
    metadata = node.attributes['razor_metadata'].to_dict()
    uuid = metadata['razor_active_model_uuid']
    return razor.get_active_model_pass(uuid)['password']
