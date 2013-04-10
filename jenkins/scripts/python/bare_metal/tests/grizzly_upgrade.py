from subprocess import check_call, CalledProcessError
import argparse
import sys
import os
from chef import ChefAPI, Search, Node
from opencenterclient.client import OpenCenterEndpoint
from razor_api import razor_api

# Parse arguments from the cmd line
parser = argparse.ArgumentParser()
parser.add_argument('--name', action="store", dest="name",
                    required=False, default="test",
                    help="Name for the opencenter chef environment")
parser.add_argument('--os', action="store", dest="os", required=False,
                    default='ubuntu',
                    help="Operating System to use for opencenter")
parser.add_argument('--url', action="store", dest="url",
                    required=False,
                    default='http://ubuntu-cloud.archive.canonical.com/ubuntu precise-updates/grizzly',
                    help="Update Resource url")
parser.add_argument('--file', action="store", dest="file", required=False,
                    default="deb/etc/apt/sources.list.d/grizzly.list",
                    help="File to place new resource")

#Defaulted arguments
parser.add_argument('--razor_ip', action="store", dest="razor_ip",
                    default="198.101.133.3",
                    help="IP for the Razor server")
parser.add_argument('--chef_url', action="store", dest="chef_url",
                    default="https://198.101.133.3:443", required=False,
                    help="client for chef")
parser.add_argument('--chef_client', action="store", dest="chef_client",
                    default="jenkins", required=False, help="client for chef")
parser.add_argument('--chef_client_pem', action="store",
                    dest="chef_client_pem",
                    default="%s/.chef/jenkins.pem" % os.getenv("HOME"),
                    required=False, help="client pem for chef")
results = parser.parse_args()


def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    """Runs a command over an ssh connection"""
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False,
                'retrun': None,
                'exception': cpe,
                'command': command}


apt_source = "deb %s main" % results.url
apt_file = results.file
# commands = ["echo %s > %s" % (apt_source, apt_file),
#             'apt-get update',
#             'apt-get dist-upgrade -y']
commands = ["echo %s > %s" % (apt_source, apt_file)]

razor = razor_api(results.razor_ip)
with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
    # Make sure environment exists
    env = "%s-%s-opencenter" % (results.name, results.os)
    if not Search("environment").query("name:%s" % env):
        print "environment %s not found" % env
        sys.exit(1)
    query = "in_use:\"server\" AND chef_environment:%s" % env
    opencenter_server = Node(next(node.name for node in
                                  Search('node').query(query)))
    opencenter_server_ip = opencenter_server.attributes['ipaddress']
    ep = OpenCenterEndpoint("https://%s:8443" % opencenter_server_ip,
                            user="admin",
                            password="password")
    chef_envs = []
    infrastructure_nodes = ep.nodes.filter('name = "Infrastructure"')
    for node_id in infrastructure_nodes.keys():
        chef_env = infrastructure_nodes[node_id].facts['chef_environment']
        chef_envs.append(chef_env)
    for node in ep.nodes.filter('facts.chef_environment = "test_cluster"'):
        if 'agent' in node.facts['backends']:
            ipaddress = Node(node.name).attributes['ipaddress']
            uuid = node.attributes['razor_metadata']['razor_active_model_uuid']
            password = razor.get_active_model_pass(uuid)['password']
            for command in commands:
                run_remote_ssh_cmd(ipaddress, 'root', password, command)
            # Run chef client?
