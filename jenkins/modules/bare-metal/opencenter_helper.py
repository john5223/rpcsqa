from opencenterclient.client import OpenCenterEndpoint
from chef import ChefAPI, Search
import sys

chef_url = ''
chef_client_pem = None
chef_client = ''


def openstack_endpoints(name='test', os='ubuntu'):
    with ChefAPI(chef_url, chef_client_pem, chef_client):
        # Make sure environment exists
        env = "%s-%s-opencenter" % (name, os)
        if not Search("environment").query("name:%s" % env):
            print "environment %s not found" % env
            sys.exit(1)
        query = "in_use:\"server\" AND chef_environment:%s" % (os, env)
        opencenter_server = Search('node').query(query)
        ep_url = "https://%s:8443" % opencenter_server.ipaddress
        ep = OpenCenterEndpoint(ep_url,
                                user="admin",
                                password="password")
        infrastructure_nodes = ep.nodes.filter('name = "Infrastructure"')
        for node_id in infrastructure_nodes.keys():
            ha = infrastructure_nodes[node_id].facts["ha_infra"]
            endpoint = None
            if ha:
                endpoint = infrastructure_nodes[node_id].facts["nova_api_vip"]
            else:
                endpoint = next(node for node in ep.nodes
                                if "nova-controller" in node.facts["backends"])
            yield endpoint
            
