import sys
import time
from chef import Search, Node, Client
from razor_api import razor_api
from server_helper import run_remote_ssh_cmd

razor_ip = '198.101.133.3'
razor = razor_api(razor_ip)


def cleanup_environment(chef_environment):
    """
    @param chef_environment
    """
    nodes = Search('node').query("chef_environment:%s AND NOT in_use:0") % \
        chef_environment
    for n in nodes:
        erase_node(n)


def erase_node(name):
    """
    @param name
    """
    print "Deleting: %s" % (name)
    node = Node(name)
    am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
    run = run_remote_ssh_cmd(node['ipaddress'],
                             'root',
                             razor.get_active_model_pass(am_uuid)['password'],
                             "reboot 0")
    if not run['success']:
        print "Error rebooting server %s " % node['ipaddress']
        # TODO: return failure
        sys.exit(1)
    #Knife node remove; knife client remove
    Client(name).delete()
    Node(name).delete()
    #Remove active model
    razor.remove_active_model(am_uuid)
    time.sleep(15)
